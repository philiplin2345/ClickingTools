import keyboard
import pyautogui
import time
import random
import numpy as np
import cv2
import functools
import json
import os
from threading import Lock
import threading
from tqdm import tqdm

CONFIG_FILE = "areas_config.json"
ANCHORS_DIR = os.path.join("images", "anchors")

# Baseline reference origin (top-left of searching_areas["prayers"] / prot_mage at 1.0x scale)
BASELINE_ORIGIN = (1888, 1101)

# Previous area definitions remain the same (used as 1.0x reference baseline)
BASELINE_CLICKING_AREAS = {
    "inventory_tag": (1957, 873, 1984, 906),
    "last_inventory_spot": (2048, 1267, 2072, 1290),
    "prayer_tag": (2056, 874, 2083, 909),
    "magic_tag": (2105, 876, 2136, 905),
    "spec": (1931, 251, 1952, 272),
    "prot_mage": (1888, 1101, 1927, 1143),
    "prot_range": (1948, 1101, 1985, 1138),
    "prot_melee": (2008, 1101, 2054, 1147),
    "prot_item": (1830, 1101, 1875, 1145),
    "rigour": (1943, 1213, 1992, 1264),
    "sgs": "images/sgs.png",
    "rock1": (1363, 721, 1469, 817),
    "rock2": (1039, 463, 1159, 546),
    "rock3": (680, 756, 791, 854),
    "quick_prayers": (1886, 169, 1897, 182)
}

# Master prayer icon templates used during F10 / startup calibration to lock in exact prayer coordinates
PRAYER_TEMPLATES = {
    "prot_mage": "images/protect_from_mage.png",
    "prot_range": "images/protect_from_range.png",
    "prot_melee": "images/protect_from_melee.png",
    "prot_item": "images/protect_item.png",
    "rigour": "images/rigour.png",
}

BASELINE_SEARCHING_AREAS = {
    "prayers": (1875, 1090, 2068, 1165),
    "rigour": (1925, 1195, 2018, 1280),
    "prot_item": (1835, 920, 2115, 1300),
    "prayer_panel": (1835, 920, 2115, 1300),
    "inventory": (1835, 920, 2100, 1050),
    "alarm_patch": (1600, 920, 1640, 960)
}

# Reference templates and their top-left offset (dx, dy) from BASELINE_ORIGIN at 1.0x scale
ANCHOR_TEMPLATES = [
    ("prot_mage", "images/protect_from_mage.png", (0, 0)),
    ("prot_range", "images/protect_from_range.png", (60, 0)),
    ("prot_melee", "images/protect_from_melee.png", (120, 0)),
    ("prayer_tag", os.path.join(ANCHORS_DIR, "prayer_tag.png"), (168, -227)),
    ("inventory_tag", os.path.join(ANCHORS_DIR, "inventory_tag.png"), (69, -228)),
    ("magic_tag", os.path.join(ANCHORS_DIR, "magic_tag.png"), (217, -225)),
]

clicking_areas = dict(BASELINE_CLICKING_AREAS)
searching_areas = dict(BASELINE_SEARCHING_AREAS)
ui_scale = 1.0

areas_set1 = [
    (50, 50, 150, 150),
    (200, 200, 300, 300),
    (350, 350, 450, 450)
]

areas_set2 = [
    (500, 50, 600, 150),
    (650, 200, 750, 300),
    (800, 350, 900, 450)
]

areas_set3 = [
    (950, 50, 1050, 150),
    (1100, 200, 1200, 300),
    (1250, 350, 1350, 450)
]
pyautogui.PAUSE = 0.05
last_execution_time = 0
execution_lock = Lock()
MIN_DELAY = 0.2  # Minimum delay in seconds

clicking = False
click_count = 0
initial_point = None
click_thread = None
progress_bar = None

# Wilderness Player Alarm watcher state (toggled by F11)
alarm_watching = False
alarm_thread = None
ALARM_POLL_INTERVAL = 0.025  # 25ms (~40 Hz, ~24 checks per OSRS tick)
ALARM_COOLDOWN = 4.0         # Seconds to pause/disarm after triggering teleport


def timing_decorator(func):
    @functools.wraps(func)  # Preserve the original function's metadata
    def wrapper(*args, **kwargs):
        start_time = time.time()  # Record the start time
        result = func(*args, **kwargs)  # Call the original function
        end_time = time.time()  # Record the end time
        execution_time = end_time - start_time  # Calculate execution time
        print(f"Function '{func.__name__}' executed in {execution_time:.4f} seconds.")
        return result  # Return the result of the function
    return wrapper


def throttle(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        global last_execution_time
        with execution_lock:
            current_time = time.time()
            time_since_last_execution = current_time - last_execution_time
            if time_since_last_execution < MIN_DELAY:
                time.sleep(MIN_DELAY - time_since_last_execution)
            result = func(*args, **kwargs)
            last_execution_time = time.time()
        return result
    return wrapper


def save_areas_config():
    """Save current clicking_areas, searching_areas, baseline_prayer_boxes, and ui_scale to a JSON file."""
    data = {
        "ui_scale": ui_scale,
        "clicking_areas": {
            k: list(v) if isinstance(v, tuple) else v
            for k, v in clicking_areas.items()
        },
        "searching_areas": {
            k: list(v) if isinstance(v, tuple) else v
            for k, v in searching_areas.items()
        },
        "baseline_prayer_boxes": {
            k: list(BASELINE_CLICKING_AREAS[k])
            for k in PRAYER_TEMPLATES
            if isinstance(BASELINE_CLICKING_AREAS.get(k), tuple)
        }
    }
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
        print(f"[Config] Saved calibrated areas to '{CONFIG_FILE}' (scale={ui_scale:.3f}).")
    except Exception as exc:
        print(f"[Config] Failed to save config: {exc}")


def load_areas_config():
    """Load persisted clicking_areas, searching_areas, and ui_scale from disk if available."""
    global clicking_areas, searching_areas, ui_scale
    if not os.path.exists(CONFIG_FILE):
        return False
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        ui_scale = float(data.get("ui_scale", 1.0))
        for k, v in data.get("clicking_areas", {}).items():
            # Ensure prayer keys are always coordinate tuples even if loading an older config
            if k in PRAYER_TEMPLATES and not isinstance(v, (list, tuple)):
                continue
            clicking_areas[k] = tuple(v) if isinstance(v, list) else v
        for k, v in data.get("searching_areas", {}).items():
            searching_areas[k] = tuple(v) if isinstance(v, list) else v
        for k, v in data.get("baseline_prayer_boxes", {}).items():
            if k in PRAYER_TEMPLATES and isinstance(v, list) and len(v) == 4:
                BASELINE_CLICKING_AREAS[k] = tuple(v)
        print(f"[Config] Loaded calibrated areas from '{CONFIG_FILE}' (scale={ui_scale:.3f}).")
        return True
    except Exception as exc:
        print(f"[Config] Failed to load '{CONFIG_FILE}': {exc}")
        return False


def match_template_multiscale(screen_gray, template_gray, scales=None, threshold=0.78):
    """
    Search for template_gray in screen_gray across candidate scales.
    Returns (best_val, best_loc, best_scale, (matched_w, matched_h)) or None if below threshold.
    """
    if scales is None:
        # Check 1.0 first; if strong match, return immediately for speed
        scales = [1.0] + [round(s, 2) for s in np.linspace(0.6, 1.8, 25) if round(s, 2) != 1.0]

    sh, sw = screen_gray.shape[:2]
    th, tw = template_gray.shape[:2]

    best_val = -1.0
    best_loc = None
    best_scale = 1.0
    best_size = (tw, th)

    for s in scales:
        rw = max(4, int(round(tw * s)))
        rh = max(4, int(round(th * s)))
        if rw >= sw or rh >= sh:
            continue

        resized = template_gray if s == 1.0 else cv2.resize(
            template_gray, (rw, rh), interpolation=cv2.INTER_AREA if s < 1.0 else cv2.INTER_LINEAR
        )
        res = cv2.matchTemplate(screen_gray, resized, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(res)

        if max_val > best_val:
            best_val = max_val
            best_loc = max_loc
            best_scale = s
            best_size = (rw, rh)
            # Early exit if 1.0x match is already very high confidence
            if s == 1.0 and best_val >= 0.88:
                break

    if best_val >= threshold and best_loc is not None:
        return best_val, best_loc, best_scale, best_size
    return None


def _derive_box(base_box, origin_x, origin_y, scale, screen_w, screen_h):
    """Compute a scaled bounding box (x1, y1, x2, y2) from BASELINE_ORIGIN."""
    bx1, by1, bx2, by2 = base_box
    ox, oy = BASELINE_ORIGIN
    x1 = int(round(origin_x + (bx1 - ox) * scale))
    y1 = int(round(origin_y + (by1 - oy) * scale))
    x2 = int(round(origin_x + (bx2 - ox) * scale))
    y2 = int(round(origin_y + (by2 - oy) * scale))

    x1 = max(0, min(x1, screen_w - 2))
    y1 = max(0, min(y1, screen_h - 2))
    x2 = max(x1 + 1, min(x2, screen_w - 1))
    y2 = max(y1 + 1, min(y2, screen_h - 1))
    return (x1, y1, x2, y2)


@timing_decorator
def refresh_areas(open_prayer_tab=False):
    """
    Scan the full screen for reference icons (prayers or saved tab anchors),
    derive all clicking_areas and searching_areas using relative offsets,
    lock in constant (x1, y1, x2, y2) coordinates for all prayer icons,
    crop updated anchor/prayer templates, and persist them to CONFIG_FILE.
    """
    global clicking_areas, searching_areas, ui_scale

    print("\n[Refresh] Scanning screen for OSRS UI reference icons...")
    screenshot_pil = pyautogui.screenshot()
    screen_bgr = cv2.cvtColor(np.array(screenshot_pil), cv2.COLOR_RGB2BGR)
    screen_gray = cv2.cvtColor(screen_bgr, cv2.COLOR_BGR2GRAY)
    screen_h, screen_w = screen_gray.shape[:2]

    matched_anchors = {}
    for name, path, offset in ANCHOR_TEMPLATES:
        # Prefer calibrated crop in images/anchors/ if available, falling back to master template
        anchor_override = os.path.join(ANCHORS_DIR, f"{name}.png")
        candidate_paths = [anchor_override, path] if anchor_override != path else [path]
        for cpath in candidate_paths:
            if not os.path.exists(cpath):
                continue
            tmpl = cv2.imread(cpath, 0)
            if tmpl is None:
                continue
            match = match_template_multiscale(screen_gray, tmpl, threshold=0.78)
            if match is not None:
                val, loc, scale_est, size = match
                matched_anchors[name] = {
                    "val": val,
                    "loc": loc,
                    "scale": scale_est,
                    "size": size,
                    "offset": offset,
                }
                print(f"  -> Matched '{name}' at {loc} (confidence={val:.3f}, scale={scale_est:.2f})")
                break

    if not matched_anchors:
        print(
            "[Refresh] Could not find reference icons on screen. "
            "Make sure the OSRS Prayer tab is open and visible, then press F10 to rescan."
        )
        return False

    # If at least 2 protection prayers matched, compute origin exclusively from them (highest accuracy)
    prayer_keys = [k for k in ("prot_mage", "prot_range", "prot_melee") if k in matched_anchors]
    ref_anchors = (
        [matched_anchors[k] for k in prayer_keys]
        if len(prayer_keys) >= 2
        else list(matched_anchors.values())
    )

    ui_scale = float(np.median([m["scale"] for m in ref_anchors]))
    origin_x = float(np.median([m["loc"][0] - m["offset"][0] * ui_scale for m in ref_anchors]))
    origin_y = float(np.median([m["loc"][1] - m["offset"][1] * ui_scale for m in ref_anchors]))

    # Update all coordinate tuple entries in clicking_areas and searching_areas
    for key, base_val in BASELINE_CLICKING_AREAS.items():
        if isinstance(base_val, tuple):
            clicking_areas[key] = _derive_box(base_val, origin_x, origin_y, ui_scale, screen_w, screen_h)
        else:
            clicking_areas[key] = base_val

    for key, base_val in BASELINE_SEARCHING_AREAS.items():
        if isinstance(base_val, tuple):
            searching_areas[key] = _derive_box(base_val, origin_x, origin_y, ui_scale, screen_w, screen_h)

    os.makedirs(ANCHORS_DIR, exist_ok=True)
    opened_prayer_temporarily = False

    # If Prayer tab is not currently open during F10 calibration, open it briefly to scan exact prayer positions
    if len(prayer_keys) < 2 and open_prayer_tab:
        # While Prayer tab is closed, crop a clean unselected prayer_tag anchor
        px1, py1, px2, py2 = clicking_areas["prayer_tag"]
        p_crop = screen_bgr[py1:py2, px1:px2]
        if p_crop.size > 0:
            cv2.imwrite(os.path.join(ANCHORS_DIR, "prayer_tag.png"), p_crop)

        print("  -> Opening Prayer tab briefly to calibrate exact prayer icon positions...")
        fast_click_spot(clicking_areas["prayer_tag"])
        time.sleep(0.10)
        screenshot_pil = pyautogui.screenshot()
        screen_bgr = cv2.cvtColor(np.array(screenshot_pil), cv2.COLOR_RGB2BGR)
        screen_gray = cv2.cvtColor(screen_bgr, cv2.COLOR_BGR2GRAY)
        opened_prayer_temporarily = True

    # Scan the Prayer panel for all 5 prayers in PRAYER_TEMPLATES to lock in their exact coordinates
    px1, py1, px2, py2 = searching_areas.get("prayer_panel", (1835, 920, 2115, 1300))
    panel_gray = screen_gray[py1:py2, px1:px2]
    panel_bgr = screen_bgr[py1:py2, px1:px2]

    matched_prayers_count = 0
    if panel_gray.size > 0:
        for prayer_key, master_path in PRAYER_TEMPLATES.items():
            if not os.path.exists(master_path):
                continue
            tmpl = cv2.imread(master_path, 0)
            if tmpl is None:
                continue
            pmatch = match_template_multiscale(
                panel_gray, tmpl, scales=[ui_scale, 1.0], threshold=0.76
            )
            if pmatch is not None:
                pval, ploc, _, (pw, ph) = pmatch
                abs_x1 = px1 + ploc[0]
                abs_y1 = py1 + ploc[1]
                abs_x2 = min(screen_w - 1, abs_x1 + pw)
                abs_y2 = min(screen_h - 1, abs_y1 + ph)

                # Store constant clickable bounding box for this prayer
                clicking_areas[prayer_key] = (abs_x1, abs_y1, abs_x2, abs_y2)
                matched_prayers_count += 1

                # Also update BASELINE_CLICKING_AREAS so future non-Prayer-tab scans preserve this slot
                ox, oy = BASELINE_ORIGIN
                BASELINE_CLICKING_AREAS[prayer_key] = (
                    int(round(ox + (abs_x1 - origin_x) / ui_scale)),
                    int(round(oy + (abs_y1 - origin_y) / ui_scale)),
                    int(round(ox + (abs_x2 - origin_x) / ui_scale)),
                    int(round(oy + (abs_y2 - origin_y) / ui_scale)),
                )

                # Tighten searching_areas for backwards compatibility
                if prayer_key in searching_areas:
                    pad = max(12, int(15 * ui_scale))
                    searching_areas[prayer_key] = (
                        max(0, abs_x1 - pad),
                        max(0, abs_y1 - pad),
                        min(screen_w - 1, abs_x2 + pad),
                        min(screen_h - 1, abs_y2 + pad),
                    )

                # Save a clean anchor crop if the prayer is not currently lit up (inactive background)
                icon_crop = panel_bgr[ploc[1]:ploc[1] + ph, ploc[0]:ploc[0] + pw]
                if icon_crop.size > 0 and pval >= 0.80 and np.mean(icon_crop) < 95:
                    cv2.imwrite(os.path.join(ANCHORS_DIR, f"{prayer_key}.png"), icon_crop)

                print(f"  -> Calibrated prayer '{prayer_key}' box={clicking_areas[prayer_key]} (conf={pval:.3f})")

    # While Prayer tab is open, save clean unselected crops for inventory_tag and magic_tag
    if len(prayer_keys) >= 2 or matched_prayers_count >= 2:
        for tab_key in ("inventory_tag", "magic_tag"):
            tx1, ty1, tx2, ty2 = clicking_areas[tab_key]
            crop = screen_bgr[ty1:ty2, tx1:tx2]
            if crop.size > 0:
                cv2.imwrite(os.path.join(ANCHORS_DIR, f"{tab_key}.png"), crop)
        # Also save prayer_tag if it doesn't exist yet
        prayer_tag_path = os.path.join(ANCHORS_DIR, "prayer_tag.png")
        if not os.path.exists(prayer_tag_path):
            tx1, ty1, tx2, ty2 = clicking_areas["prayer_tag"]
            crop = screen_bgr[ty1:ty2, tx1:tx2]
            if crop.size > 0:
                cv2.imwrite(prayer_tag_path, crop)

    # Check if optional orb templates exist for quick_prayers / spec (handles arbitrary window height)
    for orb_key in ("quick_prayers", "spec"):
        orb_path = os.path.join(ANCHORS_DIR, f"{orb_key}.png")
        if os.path.exists(orb_path):
            orb_tmpl = cv2.imread(orb_path, 0)
            if orb_tmpl is not None:
                orb_match = match_template_multiscale(
                    screen_gray, orb_tmpl, scales=[ui_scale, 1.0], threshold=0.80
                )
                if orb_match is not None:
                    _, oloc, _, (ow, oh) = orb_match
                    clicking_areas[orb_key] = (oloc[0], oloc[1], oloc[0] + ow, oloc[1] + oh)

    if opened_prayer_temporarily:
        fast_click_spot(clicking_areas["inventory_tag"])

    save_areas_config()
    print(f"[Refresh] Areas updated successfully (origin=({int(origin_x)}, {int(origin_y)}), scale={ui_scale:.3f}).")
    return True


def on_f10_press(e):
    if e.event_type == keyboard.KEY_DOWN:
        refresh_areas(open_prayer_tab=True)


def weighted_random_point_in_area(area, center_weight=0.7):
    x_min, y_min, x_max, y_max = area
    center_x, center_y = (x_min + x_max) / 2, (y_min + y_max) / 2
    width, height = x_max - x_min, y_max - y_min
    
    while True:
        # Generate a point using a normal distribution
        x = int(random.gauss(center_x, width * (1 - center_weight) / 2))
        y = int(random.gauss(center_y, height * (1 - center_weight) / 2))
        
        # Check if the point is within the area
        if x_min <= x <= x_max and y_min <= y <= y_max:
            return (x, y)

# def weighted_random_point_in_area(area, center_weight=0.7):
#     x_min, y_min, x_max, y_max = area
#     center_x, center_y = (x_min + x_max) / 2, (y_min + y_max) / 2
#     width, height = x_max - x_min, y_max - y_min

#     # Generate a point using a uniform distribution, then apply weighting
#     x = random.uniform(x_min, x_max)
#     y = random.uniform(y_min, y_max)

#     # Apply weighting towards the center
#     x = int(x * (1 - center_weight) + center_x * center_weight)
#     y = int(y * (1 - center_weight) + center_y * center_weight)

#     return (x, y)
def double_click_spot(area):
    spot = weighted_random_point_in_area(area)
    pyautogui.moveTo(spot[0], spot[1])
    pyautogui.click(spot[0], spot[1])
    time.sleep(random.uniform(0.05, 0.1))
    pyautogui.click(spot[0], spot[1])

def click_spot(area):
    spot = weighted_random_point_in_area(area)
    pyautogui.moveTo(spot[0], spot[1])
    pyautogui.click(spot[0], spot[1])
    # time.sleep(random.uniform(0.1, 0.5))

def click_spots(areas):
    for area in areas:
        spot = weighted_random_point_in_area(area)
        pyautogui.click(spot[0], spot[1])
        time.sleep(random.uniform(0.1, 0.5))


@timing_decorator
# @throttle
def on_f4_press(e):
    if e.event_type == keyboard.KEY_DOWN:
        double_click_spot(clicking_areas["quick_prayers"])
        click_spot(clicking_areas["inventory_tag"])


@timing_decorator
# @throttle
def on_f5_press(e):
    if e.event_type == keyboard.KEY_DOWN:
        click_spot(clicking_areas["prayer_tag"])
        time.sleep(random.uniform(0.05, 0.08))
        click_spot(clicking_areas["prot_mage"])
        time.sleep(random.uniform(0.05, 0.08))
        click_spot(clicking_areas["rigour"])
        click_spot(clicking_areas["inventory_tag"])


@timing_decorator
# @throttle
def on_f6_press(e):
    if e.event_type == keyboard.KEY_DOWN:
        click_spot(clicking_areas["prayer_tag"])
        time.sleep(random.uniform(0.05, 0.08))
        click_spot(clicking_areas["prot_range"])
        time.sleep(random.uniform(0.05, 0.08))
        click_spot(clicking_areas["rigour"])
        click_spot(clicking_areas["inventory_tag"])


@timing_decorator
# @throttle
def on_f7_press(e):
    if e.event_type == keyboard.KEY_DOWN:
        click_spot(clicking_areas["prayer_tag"])
        time.sleep(random.uniform(0.05, 0.08))
        click_spot(clicking_areas["prot_melee"])
        click_spot(clicking_areas["inventory_tag"])

@timing_decorator
# @throttle
def on_f8_press(e):
    if e.event_type == keyboard.KEY_DOWN:
        click_spot(clicking_areas["inventory_tag"])
        time.sleep(random.uniform(0.05, 0.1))
        find_and_click_image(clicking_areas["sgs"],searching_areas["inventory"])
        time.sleep(random.uniform(0.7, 0.8))
        click_spot(clicking_areas["spec"])
    
def fast_click_spot(area):
    """Click a spot immediately bypassing pyautogui's global 50ms pause per action."""
    spot = weighted_random_point_in_area(area)
    pyautogui.moveTo(spot[0], spot[1], _pause=False)
    pyautogui.click(spot[0], spot[1], _pause=False)


@timing_decorator
def emergency_teleport(source="manual"):
    """Interrupt any ongoing clicking, click inventory tab + teleport item, then enable Protect Item prayer."""
    global clicking
    clicking = False
    fast_click_spot(clicking_areas["inventory_tag"])
    time.sleep(random.uniform(0.015, 0.025))
    fast_click_spot(clicking_areas["last_inventory_spot"])

    # Immediately switch to Prayer tab and click calibrated Protect Item spot in case teleblock landed
    time.sleep(random.uniform(0.025, 0.04))
    fast_click_spot(clicking_areas["prayer_tag"])
    time.sleep(random.uniform(0.03, 0.05))
    fast_click_spot(clicking_areas["prot_item"])
    time.sleep(random.uniform(0.015, 0.025))
    fast_click_spot(clicking_areas["inventory_tag"])
    print(f"[Teleport] Emergency teleport + Protect Item triggered ({source})!")


def on_esc_press(e):
    if e.event_type == keyboard.KEY_DOWN:
        emergency_teleport(source="Esc key")


def is_alarm_flash_detected(patch_bgr):
    """
    Detect RuneLite Wilderness Player Alarm screen flash in a sampled BGR viewport patch.
    Designed for Magenta (#FF00FF) flash at >=35% opacity (recommended: 50%-75% opacity),
    and also supports solid high-opacity Red (#FF0000 at >=70% opacity).
    """
    b = patch_bgr[:, :, 0].astype(np.int16)
    g = patch_bgr[:, :, 1].astype(np.int16)
    r = patch_bgr[:, :, 2].astype(np.int16)

    # 1. Magenta (#FF00FF) flash check: high R and B, suppressed G (works down to ~35% opacity)
    magenta_mask = (r >= 95) & (b >= 95) & ((r - g) >= 65) & ((b - g) >= 65)
    if np.mean(magenta_mask) >= 0.70:
        return True

    # 2. Pure Red (#FF0000) flash fallback: very high R, very low G and B across entire patch
    red_mask = (r >= 175) & (g <= 55) & (b <= 55) & ((r - g) >= 130)
    if np.mean(red_mask) >= 0.85:
        return True

    return False


def alarm_watcher_loop():
    """Background loop that polls searching_areas['alarm_patch'] for the alarm flash."""
    global alarm_watching
    while alarm_watching:
        try:
            x1, y1, x2, y2 = searching_areas.get("alarm_patch", (1600, 920, 1640, 960))
            w = max(8, x2 - x1)
            h = max(8, y2 - y1)
            shot = pyautogui.screenshot(region=(x1, y1, w, h))
            patch_bgr = cv2.cvtColor(np.array(shot), cv2.COLOR_RGB2BGR)

            if is_alarm_flash_detected(patch_bgr):
                emergency_teleport(source="Wilderness Player Alarm")
                alarm_watching = False
                print(
                    "[Alarm] Auto-teleport triggered and DISARMED to prevent extra clicks. "
                    "Press F11 when ready to re-arm."
                )
                break
        except Exception as exc:
            print(f"[Alarm] Watcher error: {exc}")

        time.sleep(ALARM_POLL_INTERVAL)


def toggle_alarm_watcher(e):
    """Toggle the Wilderness Player Alarm auto-teleport watcher on F11 press."""
    global alarm_watching, alarm_thread
    if e.event_type == keyboard.KEY_DOWN:
        if not alarm_watching:
            alarm_watching = True
            alarm_thread = threading.Thread(target=alarm_watcher_loop, daemon=True)
            alarm_thread.start()
            print(
                f"[Alarm] Auto-teleport ARMED (monitoring patch {searching_areas.get('alarm_patch')}). "
                "Press F11 to disarm."
            )
        else:
            alarm_watching = False
            print("[Alarm] Auto-teleport DISARMED.")

def on_f12_press(e):
    if e.event_type == keyboard.KEY_DOWN:
        for _ in range(120):
            click_spot(clicking_areas["rock1"])
            time.sleep(random.uniform(2.7, 2.8))
            click_spot(clicking_areas["rock2"])
            time.sleep(random.uniform(2.7, 2.8))
            click_spot(clicking_areas["rock3"])
            time.sleep(random.uniform(2.7, 2.8))

# Define the search area for the image (x_min, y_min, x_max, y_max)
SEARCH_AREA = (500, 300, 1000, 600)  # Adjust these coordinates as needed

@timing_decorator
def find_and_click_image(image_path,search_area):
    start_time = time.time()
    
    # Read the template image first so we can ensure search_area is at least as large as template
    before_read_time = time.time()
    template = cv2.imread(image_path, 0)
    if template is None:
        print(f"Template image not found or unreadable: {image_path}")
        return
    if ui_scale != 1.0:
        th, tw = template.shape[:2]
        rw = max(4, int(round(tw * ui_scale)))
        rh = max(4, int(round(th * ui_scale)))
        template = cv2.resize(
            template, (rw, rh), interpolation=cv2.INTER_AREA if ui_scale < 1.0 else cv2.INTER_LINEAR
        )
    after_read_time = time.time()

    # Ensure search area is at least as large as the template to prevent OpenCV assertion errors
    x_min, y_min, x_max, y_max = search_area
    th, tw = template.shape[:2]
    region_w = max(x_max - x_min, tw + 10)
    region_h = max(y_max - y_min, th + 10)

    # Take a screenshot of only the search area
    screenshot = pyautogui.screenshot(region=(x_min, y_min, region_w, region_h))
    screenshot = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
    # Perform template matching
    result = cv2.matchTemplate(cv2.cvtColor(screenshot, cv2.COLOR_BGR2GRAY), template, cv2.TM_CCOEFF_NORMED)
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
    match_time = time.time()
    # If the image is found (you can adjust the threshold)
    if max_val > 0.8:
        # Calculate the center and dimensions of the found image
        h, w = template.shape
        center_x = x_min + max_loc[0] + w // 2
        center_y = y_min + max_loc[1] + h // 2
        
        # Define the area of the found image
        image_area = (x_min + max_loc[0], y_min + max_loc[1], 
                        x_min + max_loc[0] + w, y_min + max_loc[1] + h)
        
        # Get a weighted random point within the image area
        click_x, click_y = weighted_random_point_in_area(image_area)

        # Move the mouse to the point (this initiates the hover)
        pyautogui.moveTo(click_x, click_y)
        
        # Wait for 0.05 seconds
        time.sleep(random.uniform(0.11, 0.125))

        pre_click_time = time.time()
        # Click on the weighted random point
        pyautogui.click(click_x, click_y)
        
        end_time = time.time()
        print(f"Image found and clicked in {(end_time - start_time) * 1000:.2f} ms. max_val is {max_val}. start-before = {before_read_time-start_time} imageread= {after_read_time-before_read_time} matchtime {match_time -after_read_time} click time = {end_time-pre_click_time} end-after {end_time-after_read_time}")
    else:
        print(f"Image not found in the search area max value is {max_val}")

def random_point_near(x, y, max_distance):
    if random.random() < 0.99:  # 75% chance of not shifting
        return (x, y)
    return (
        x + random.randint(-max_distance, max_distance),
        y + random.randint(-max_distance, max_distance)
    )

def stop_clicking():
    global clicking, click_count, click_thread
    clicking = False
    if click_thread and click_thread.is_alive():
        click_thread.join()
    print(f"\nDouble-clicking stopped after {click_count} clicks.")
    click_thread = None

def double_click_task():
    global clicking, click_count, initial_point, progress_bar
    
    click_x, click_y = initial_point
    
    # Initialize the progress bar
    progress_bar = tqdm(total=30, desc="Double-clicking", unit="clicks")
    
    while clicking and click_count < 30:
        # Calculate new click point (75% chance of no shift, 25% chance of max 3 pixels shift)
        click_x, click_y = random_point_near(click_x, click_y, 3)
        
        # Ensure the new point is within 10 pixels of the initial point
        click_x = max(initial_point[0] - 10, min(initial_point[0] + 10, click_x))
        click_y = max(initial_point[1] - 10, min(initial_point[1] + 10, click_y))
        pyautogui.moveTo(click_x, click_y)
        
        # Wait for 0.05 seconds
        time.sleep(random.uniform(0.11, 0.125))
        # Perform double click
        pyautogui.click(click_x, click_y)
        pyautogui.click(click_x, click_y)
        click_count += 1
        
        # Update the progress bar
        progress_bar.update(1)
        
        # Wait for random interval between 590 and 610 ms
        time.sleep(random.uniform(0.100, 0.110))
    
    # Close the progress bar
    progress_bar.close()

    # Call stop_clicking() to ensure proper cleanup
    stop_clicking()

def toggle_clicking(e):
    global clicking, click_count, initial_point, click_thread
    
    if e.event_type == keyboard.KEY_DOWN:
        if not clicking:
            # Start clicking
            clicking = True
            click_count = 0
            initial_point = pyautogui.position()
            click_thread = threading.Thread(target=double_click_task)
            click_thread.start()
            print("Double-clicking started.")
        else:
            # Stop clicking
            stop_clicking()


# Load persisted areas if available, then attempt an initial screen scan
load_areas_config()
refresh_areas()

# Set up the listeners for F4-F10 and Esc keys
keyboard.on_press_key("f4", on_f4_press)
keyboard.on_press_key("f5", on_f5_press)
keyboard.on_press_key("f6", on_f6_press)
keyboard.on_press_key("f7", on_f7_press)
keyboard.on_press_key("f8", on_f8_press)
keyboard.on_press_key("f9", toggle_clicking)
keyboard.on_press_key("f10", on_f10_press)
keyboard.on_press_key("f11", toggle_alarm_watcher)
keyboard.on_press_key("esc", on_esc_press)
# keyboard.on_press_key("f12", on_f12_press)
print("Listening for F4-F9, Esc, F10 (refresh areas), and F11 (toggle PKer alarm auto-tele). Press Ctrl+C to exit.")

# Keep the script running
keyboard.wait()

keyboard.wait()