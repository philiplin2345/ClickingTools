import keyboard
import pyautogui
import time
import random
import ctypes
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
    "prot_range": (1946, 1106, 1983, 1143),
    "prot_melee": (1998, 1099, 2044, 1145),
    "prot_item": (1829, 1045, 1877, 1091),
    "rigour": (1941, 1215, 1986, 1253),
    "augury": (1998, 1216, 2040, 1255),
    "piety": (1884, 1223, 1930, 1247),
    "ice_barrage": (1910, 1240, 1944, 1277),
    "blood_barrage": (1840, 1246, 1871, 1277),
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
    "augury": "images/augury.png",
    "piety": "images/piety.png",
}

# Master spell icon templates used during F10 / startup calibration to lock in exact spell coordinates
# Note: blood_barrage is always derived directly 1 column left of ice_barrage so it never false-matches shadow/smoke barrage
SPELL_TEMPLATES = {
    "ice_barrage": "images/ice_barrage.png",
}

# Special Attack minimap orb templates (unactive vs active state)
SPEC_ORB_TEMPLATES = {
    "unactive": "images/spec_orb_unactive.png",
    "active": "images/spec_orb_active.png",
}

GMAUL_TEMPLATE_PATH = "images/granite_maul.png"

# Combo-eat item templates (Hard food -> Saradomin brew -> Karambwan) with dose counts
COMBO_FOOD_TEMPLATES = {
    "hard_food": [
        ("shark", "images/shark.png", 1),
        ("blighted_manta_ray", "images/blighted_manta_ray.png", 1),
        ("blighted_anglerfish", "images/blighted_anglerfish.png", 1),
    ],
    "brew": [
        ("saradomin_brew_4", "images/saradomin_brew_4.png", 4),
        ("saradomin_brew_3", "images/saradomin_brew_3.png", 3),
        ("saradomin_brew_2", "images/saradomin_brew_2.png", 2),
        ("saradomin_brew_1", "images/saradomin_brew_1.png", 1),
    ],
    "karambwan": [
        ("karambwan", "images/karambwan.png", 1),
    ],
}

BASELINE_SEARCHING_AREAS = {
    "prayers": (1886, 1097, 2046, 1147),
    "prot_mage": (1886, 1099, 1929, 1145),
    "prot_range": (1944, 1104, 1985, 1145),
    "prot_melee": (1996, 1097, 2046, 1147),
    "prot_item": (1827, 1043, 1879, 1093),
    "rigour": (1939, 1213, 1988, 1255),
    "augury": (1996, 1214, 2042, 1257),
    "piety": (1882, 1221, 1932, 1249),
    "ice_barrage": (1906, 1236, 1948, 1281),
    "blood_barrage": (1836, 1242, 1875, 1281),
    "spec": (1918, 238, 1966, 286),
    "prayer_panel": (1820, 1035, 2055, 1265),
    "magic_panel": (1820, 920, 2110, 1290),
    "inventory_panel": (1842, 928, 2088, 1304),
    "inventory": (1835, 920, 2100, 1050),
    "hp_bar": (1801, 927, 1813, 1300),
    "alarm_patch": (1600, 920, 1640, 960)
}

# Reference templates and their top-left offset (dx, dy) from BASELINE_ORIGIN at 1.0x scale.
# Tab stones are listed FIRST because at least 2 of the 3 are always unselected/visible regardless of which tab is open.
ANCHOR_TEMPLATES = [
    ("prayer_tag", os.path.join(ANCHORS_DIR, "prayer_tag.png"), (166, -227)),
    ("inventory_tag", os.path.join(ANCHORS_DIR, "inventory_tag.png"), (67, -227)),
    ("magic_tag", os.path.join(ANCHORS_DIR, "magic_tag.png"), (215, -224)),
    ("prot_mage", "images/protect_from_mage.png", (0, 0)),
    ("prot_range", "images/protect_from_range.png", (58, 5)),
    ("prot_melee", "images/protect_from_melee.png", (110, -2)),
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

# Active barrage spell selected on F1 ('ice_barrage' by default, toggled to 'blood_barrage' via F12)
active_barrage_spell = "ice_barrage"


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
            for k in list(PRAYER_TEMPLATES) + list(SPELL_TEMPLATES)
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
        icon_keys = set(PRAYER_TEMPLATES) | set(SPELL_TEMPLATES)
        for k, v in data.get("clicking_areas", {}).items():
            # Ensure prayer/spell keys are always coordinate tuples even if loading an older config
            if k in icon_keys and not isinstance(v, (list, tuple)):
                continue
            clicking_areas[k] = tuple(v) if isinstance(v, list) else v
        for k, v in data.get("searching_areas", {}).items():
            searching_areas[k] = tuple(v) if isinstance(v, list) else v
        for k, v in data.get("baseline_prayer_boxes", {}).items():
            if k in icon_keys and isinstance(v, list) and len(v) == 4:
                BASELINE_CLICKING_AREAS[k] = tuple(v)
        # Always lock 'blood_barrage' directly 1 column (-72px center-to-center) left of 'ice_barrage'
        if isinstance(clicking_areas.get("ice_barrage"), tuple) and len(clicking_areas["ice_barrage"]) == 4:
            ix1, iy1, ix2, iy2 = clicking_areas["ice_barrage"]
            # ice_barrage.png (34x37) has 3px left & 7px top background padding; true 29x29 icon is at (+3..+32, +7..+36)
            icx = ix1 + 17.5 * ui_scale if (iy2 - iy1) >= int(round(34 * ui_scale)) else (ix1 + ix2) / 2.0
            icy = iy1 + 21.5 * ui_scale if (iy2 - iy1) >= int(round(34 * ui_scale)) else (iy1 + iy2) / 2.0
            bcx = icx - 72.0 * ui_scale
            bcy = icy
            r_half = max(6, int(round(10 * ui_scale)))
            clicking_areas["blood_barrage"] = (
                max(0, int(round(bcx - r_half))),
                max(0, int(round(bcy - r_half))),
                max(1, int(round(bcx + r_half))),
                max(1, int(round(bcy + r_half))),
            )
        if isinstance(BASELINE_CLICKING_AREAS.get("ice_barrage"), tuple):
            bix1, biy1, _, biy2 = BASELINE_CLICKING_AREAS["ice_barrage"]
            BASELINE_CLICKING_AREAS["blood_barrage"] = (bix1 - 69, biy1 + 7, bix1 - 40, biy1 + 36)
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


# In-memory template cache: (path, ui_scale, color_mode) -> np.ndarray
_template_cache = {}


def get_cached_template(image_path, color=False):
    """Load and cache grayscale (or BGR color) template image in memory so keypresses don't hit disk."""
    key = (image_path, ui_scale, bool(color))
    if key in _template_cache:
        return _template_cache[key]
    flag = cv2.IMREAD_COLOR if color else cv2.IMREAD_GRAYSCALE
    template = cv2.imread(image_path, flag)
    if template is None:
        return None
    if ui_scale != 1.0 and not str(image_path).startswith(ANCHORS_DIR):
        th, tw = template.shape[:2]
        rw = max(4, int(round(tw * ui_scale)))
        rh = max(4, int(round(th * ui_scale)))
        template = cv2.resize(
            template, (rw, rh), interpolation=cv2.INTER_AREA if ui_scale < 1.0 else cv2.INTER_LINEAR
        )
    _template_cache[key] = template
    return template


def auto_trim_crop(crop_bgr, margin=1):
    """Trim uniform background borders around an icon crop, keeping a `margin`-pixel border."""
    if crop_bgr is None or crop_bgr.size == 0:
        return crop_bgr
    h, w = crop_bgr.shape[:2]
    bg = crop_bgr[0, 0].astype(np.int16)
    diff = np.abs(crop_bgr.astype(np.int16) - bg).max(axis=2)
    ys, xs = np.where(diff > 15)
    if len(xs) == 0 or len(ys) == 0:
        return crop_bgr
    x1 = max(0, int(xs.min()) - margin)
    y1 = max(0, int(ys.min()) - margin)
    x2 = min(w, int(xs.max()) + 1 + margin)
    y2 = min(h, int(ys.max()) + 1 + margin)
    return crop_bgr[y1:y2, x1:x2]


def _calibrate_spec_orb_from_screen(screen_gray, origin_x, origin_y, screen_w, screen_h):
    """
    Scan the minimap region above the side panel for spec_orb_unactive.png or spec_orb_active.png.
    Since the spec orb is attached to the top-right minimap (not the bottom-right side panel),
    scanning the vertical column above the side panel finds its exact position at any window height.
    """
    sx1 = max(0, int(round(origin_x - 160 * ui_scale)))
    sx2 = min(screen_w, int(round(origin_x + 300 * ui_scale)))
    sy1 = 0
    sy2 = max(120, min(screen_h, int(round(origin_y - 80 * ui_scale))))

    strip_gray = screen_gray[sy1:sy2, sx1:sx2]
    if strip_gray.size == 0:
        return False

    best_match = None
    for state_key, orb_path in SPEC_ORB_TEMPLATES.items():
        if not os.path.exists(orb_path):
            continue
        orb_tmpl = cv2.imread(orb_path, 0)
        if orb_tmpl is None:
            continue
        m = match_template_multiscale(strip_gray, orb_tmpl, scales=[ui_scale, 1.0], threshold=0.76)
        if m is not None and (best_match is None or m[0] > best_match[0]):
            best_match = (*m, state_key)

    if best_match is None:
        return False

    oval, oloc, _, (ow, oh), state_key = best_match
    abs_x1 = sx1 + oloc[0]
    abs_y1 = sy1 + oloc[1]
    abs_x2 = min(screen_w - 1, abs_x1 + ow)
    abs_y2 = min(screen_h - 1, abs_y1 + oh)

    # Inset click box slightly (+4px) so random clicks always land inside the circular orb
    inset_x = max(2, int(round(4 * ui_scale)))
    inset_y = max(2, int(round(4 * ui_scale)))
    clicking_areas["spec"] = (
        abs_x1 + inset_x,
        abs_y1 + inset_y,
        max(abs_x1 + inset_x + 2, abs_x2 - inset_x),
        max(abs_y1 + inset_y + 2, abs_y2 - inset_y),
    )
    pad = max(3, int(round(4 * ui_scale)))
    searching_areas["spec"] = (
        max(0, abs_x1 - pad),
        max(0, abs_y1 - pad),
        min(screen_w - 1, abs_x2 + pad),
        min(screen_h - 1, abs_y2 + pad),
    )
    print(f"  -> Calibrated minimap 'spec' orb ({state_key}) click={clicking_areas['spec']} search={searching_areas['spec']} (conf={oval:.3f})")
    return True


@timing_decorator
def refresh_areas(open_prayer_tab=False):
    """
    Scan the full screen for reference icons (prayers or saved tab anchors),
    derive all clicking_areas and searching_areas using relative offsets,
    lock in constant (x1, y1, x2, y2) coordinates for all prayer & spell icons,
    crop updated anchor/prayer/spell templates, and persist them to CONFIG_FILE.
    """
    global clicking_areas, searching_areas, ui_scale

    print("\n[Refresh] Scanning screen for OSRS UI reference icons...")
    screenshot_pil = pyautogui.screenshot()
    screen_bgr = cv2.cvtColor(np.array(screenshot_pil), cv2.COLOR_RGB2BGR)
    screen_gray = cv2.cvtColor(screen_bgr, cv2.COLOR_BGR2GRAY)
    screen_h, screen_w = screen_gray.shape[:2]

    matched_anchors = {}
    fast_scales = [ui_scale] if ui_scale == 1.0 else [ui_scale, 1.0]

    # Pass 1: Fast check at [ui_scale, 1.0] (avoids 25-scale full-screen search when Prayer tab is closed!)
    for name, path, offset in ANCHOR_TEMPLATES:
        # On startup (open_prayer_tab=False), once 2 tab stones match, skip checking prayer icons
        if not open_prayer_tab and len(matched_anchors) >= 2 and name in ("prot_mage", "prot_range", "prot_melee"):
            continue
        anchor_override = os.path.join(ANCHORS_DIR, f"{name}.png")
        candidate_paths = [anchor_override, path] if anchor_override != path else [path]
        for cpath in candidate_paths:
            if not os.path.exists(cpath):
                continue
            tmpl = cv2.imread(cpath, 0)
            if tmpl is None:
                continue
            match = match_template_multiscale(screen_gray, tmpl, scales=fast_scales, threshold=0.78)
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

    # Pass 2: Full 25-scale fallback only if Pass 1 found nothing (e.g. UI scale changed)
    if not matched_anchors:
        for name, path, offset in ANCHOR_TEMPLATES:
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
    opened_tab_temporarily = False
    missing_prayer_anchors = any(
        not os.path.exists(os.path.join(ANCHORS_DIR, f"{pk}.png")) for pk in PRAYER_TEMPLATES
    )

    # If Prayer tab is not currently open during F10 calibration (or if any prayer anchor is missing), open it briefly
    if len(prayer_keys) < 2 and (open_prayer_tab or missing_prayer_anchors):
        # While Prayer tab is closed, crop a clean unselected prayer_tag anchor
        px1, py1, px2, py2 = clicking_areas["prayer_tag"]
        p_crop = screen_bgr[py1:py2, px1:px2]
        if p_crop.size > 0:
            cv2.imwrite(os.path.join(ANCHORS_DIR, "prayer_tag.png"), p_crop)

        print("  -> Opening Prayer tab briefly to calibrate exact prayer icon positions...")
        fast_click_spot(clicking_areas["prayer_tag"])
        time.sleep(0.15)
        screenshot_pil = pyautogui.screenshot()
        screen_bgr = cv2.cvtColor(np.array(screenshot_pil), cv2.COLOR_RGB2BGR)
        screen_gray = cv2.cvtColor(screen_bgr, cv2.COLOR_BGR2GRAY)
        opened_tab_temporarily = True

    # Scan the Prayer panel for all prayers in PRAYER_TEMPLATES only when Prayer tab is open (or during F10)
    px1, py1, px2, py2 = searching_areas.get("prayer_panel", (1820, 1035, 2055, 1265))
    panel_gray = screen_gray[py1:py2, px1:px2]
    panel_bgr = screen_bgr[py1:py2, px1:px2]

    matched_prayers_count = 0
    if panel_gray.size > 0 and (len(prayer_keys) >= 1 or open_prayer_tab or missing_prayer_anchors):
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

                # Tighten runtime searching_areas[prayer_key] to just the icon size (+2px margin) for fastest matching
                pad = max(2, int(round(2 * ui_scale)))
                searching_areas[prayer_key] = (
                    max(0, abs_x1 - pad),
                    max(0, abs_y1 - pad),
                    min(screen_w - 1, abs_x2 + pad),
                    min(screen_h - 1, abs_y2 + pad),
                )

                # Save a clean, tightly-trimmed anchor crop if the prayer is not currently lit up
                icon_crop = panel_bgr[ploc[1]:ploc[1] + ph, ploc[0]:ploc[0] + pw]
                if icon_crop.size > 0 and pval >= 0.80 and np.mean(icon_crop) < 95:
                    cv2.imwrite(os.path.join(ANCHORS_DIR, f"{prayer_key}.png"), auto_trim_crop(icon_crop, margin=1))

                print(f"  -> Calibrated prayer '{prayer_key}' box={clicking_areas[prayer_key]} search={searching_areas[prayer_key]} (conf={pval:.3f})")

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

    # Calibrate spells in SPELL_TEMPLATES (e.g. ice_barrage) during F10 or if magic tab is open
    missing_spell_anchors = any(
        os.path.exists(master_path) and not os.path.exists(os.path.join(ANCHORS_DIR, f"{sk}.png"))
        for sk, master_path in SPELL_TEMPLATES.items()
    )
    if open_prayer_tab or missing_spell_anchors:
        print("  -> Opening Magic tab briefly to calibrate exact spell icon positions...")
        fast_click_spot(clicking_areas["magic_tag"])
        time.sleep(0.12)
        screenshot_pil = pyautogui.screenshot()
        screen_bgr = cv2.cvtColor(np.array(screenshot_pil), cv2.COLOR_RGB2BGR)
        screen_gray = cv2.cvtColor(screen_bgr, cv2.COLOR_BGR2GRAY)
        opened_tab_temporarily = True

    mx1, my1, mx2, my2 = searching_areas.get("magic_panel", (1820, 920, 2110, 1290))
    mpanel_gray = screen_gray[my1:my2, mx1:mx2]
    mpanel_bgr = screen_bgr[my1:my2, mx1:mx2]
    if mpanel_gray.size > 0 and (open_prayer_tab or missing_spell_anchors):
        for spell_key, master_path in SPELL_TEMPLATES.items():
            if not os.path.exists(master_path):
                continue
            stmpl = cv2.imread(master_path, 0)
            if stmpl is None:
                continue
            smatch = match_template_multiscale(
                mpanel_gray, stmpl, scales=[ui_scale, 1.0], threshold=0.76
            )
            if smatch is not None:
                sval, sloc, _, (sw_icon, sh_icon) = smatch
                abs_x1 = mx1 + sloc[0]
                abs_y1 = my1 + sloc[1]
                abs_x2 = min(screen_w - 1, abs_x1 + sw_icon)
                abs_y2 = min(screen_h - 1, abs_y1 + sh_icon)

                clicking_areas[spell_key] = (abs_x1, abs_y1, abs_x2, abs_y2)
                ox, oy = BASELINE_ORIGIN
                BASELINE_CLICKING_AREAS[spell_key] = (
                    int(round(ox + (abs_x1 - origin_x) / ui_scale)),
                    int(round(oy + (abs_y1 - origin_y) / ui_scale)),
                    int(round(ox + (abs_x2 - origin_x) / ui_scale)),
                    int(round(oy + (abs_y2 - origin_y) / ui_scale)),
                )
                pad = max(2, int(round(2 * ui_scale)))
                searching_areas[spell_key] = (
                    max(0, abs_x1 - pad),
                    max(0, abs_y1 - pad),
                    min(screen_w - 1, abs_x2 + pad),
                    min(screen_h - 1, abs_y2 + pad),
                )
                spell_crop = mpanel_bgr[sloc[1]:sloc[1] + sh_icon, sloc[0]:sloc[0] + sw_icon]
                if spell_crop.size > 0 and sval >= 0.80:
                    cv2.imwrite(os.path.join(ANCHORS_DIR, f"{spell_key}.png"), auto_trim_crop(spell_crop, margin=1))
                print(f"  -> Calibrated spell '{spell_key}' box={clicking_areas[spell_key]} (conf={sval:.3f})")

    # Always lock 'blood_barrage' directly 1 column (-72px center-to-center) left of 'ice_barrage'
    if isinstance(clicking_areas.get("ice_barrage"), tuple) and len(clicking_areas["ice_barrage"]) == 4:
        ix1, iy1, ix2, iy2 = clicking_areas["ice_barrage"]
        icx = ix1 + 17.5 * ui_scale if (iy2 - iy1) >= int(round(34 * ui_scale)) else (ix1 + ix2) / 2.0
        icy = iy1 + 21.5 * ui_scale if (iy2 - iy1) >= int(round(34 * ui_scale)) else (iy1 + iy2) / 2.0
        bcx = icx - 72.0 * ui_scale
        bcy = icy
        r_half = max(6, int(round(10 * ui_scale)))
        bb_x1 = max(0, int(round(bcx - r_half)))
        bb_y1 = max(0, int(round(bcy - r_half)))
        bb_x2 = min(screen_w - 1, int(round(bcx + r_half)))
        bb_y2 = min(screen_h - 1, int(round(bcy + r_half)))
        clicking_areas["blood_barrage"] = (bb_x1, bb_y1, bb_x2, bb_y2)
        if isinstance(BASELINE_CLICKING_AREAS.get("ice_barrage"), tuple):
            bix1, biy1, _, biy2 = BASELINE_CLICKING_AREAS["ice_barrage"]
            BASELINE_CLICKING_AREAS["blood_barrage"] = (bix1 - 69, biy1 + 7, bix1 - 40, biy1 + 36)
        pad = max(2, int(round(2 * ui_scale)))
        searching_areas["blood_barrage"] = (
            max(0, bb_x1 - pad),
            max(0, bb_y1 - pad),
            min(screen_w - 1, bb_x2 + pad),
            min(screen_h - 1, bb_y2 + pad),
        )
        print(f"  -> Locked 'blood_barrage' directly left of 'ice_barrage': box={clicking_areas['blood_barrage']}")

    # Calibrate minimap Special Attack orb position (handles any window height since it's attached to minimap)
    _calibrate_spec_orb_from_screen(screen_gray, origin_x, origin_y, screen_w, screen_h)

    # Check if optional orb template exists for quick_prayers
    qp_path = os.path.join(ANCHORS_DIR, "quick_prayers.png")
    if os.path.exists(qp_path):
        qp_tmpl = cv2.imread(qp_path, 0)
        if qp_tmpl is not None:
            qp_match = match_template_multiscale(
                screen_gray, qp_tmpl, scales=[ui_scale, 1.0], threshold=0.80
            )
            if qp_match is not None:
                _, oloc, _, (ow, oh) = qp_match
                clicking_areas["quick_prayers"] = (oloc[0], oloc[1], oloc[0] + ow, oloc[1] + oh)

    if opened_tab_temporarily:
        fast_click_spot(clicking_areas["inventory_tag"])

    _template_cache.clear()
    save_areas_config()
    print(f"[Refresh] Areas updated successfully (origin=({int(origin_x)}, {int(origin_y)}), scale={ui_scale:.3f}).")
    return True


def on_f10_press(e):
    if e.event_type == keyboard.KEY_DOWN:
        refresh_areas(open_prayer_tab=True)


def weighted_random_point_in_area(area, center_weight=0.85):
    x_min, y_min, x_max, y_max = area
    center_x, center_y = (x_min + x_max) / 2.0, (y_min + y_max) / 2.0
    width, height = x_max - x_min, y_max - y_min

    # Restrict clicks to the inner 50% around the exact center so clicks never drift near icon edges
    inner_rx = max(1.0, width * 0.25)
    inner_ry = max(1.0, height * 0.25)
    inner_x_min = int(round(center_x - inner_rx))
    inner_x_max = int(round(center_x + inner_rx))
    inner_y_min = int(round(center_y - inner_ry))
    inner_y_max = int(round(center_y + inner_ry))

    while True:
        # Generate a point using a tight normal distribution centered on the icon
        x = int(round(random.gauss(center_x, max(1.0, width * (1 - center_weight) / 2))))
        y = int(round(random.gauss(center_y, max(1.0, height * (1 - center_weight) / 2))))

        # Ensure the point lands strictly within the inner center region
        if inner_x_min <= x <= inner_x_max and inner_y_min <= y <= inner_y_max:
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


def get_inventory_slot_boxes(zigzag=True, detect_hw_base=22, detect_hh_base=20):
    """
    Compute all 28 OSRS inventory slot bounding boxes (7 rows x 4 columns)
    anchored from clicking_areas['last_inventory_spot'] (which is row=6, col=3).
    If zigzag=True, odd rows scan right-to-left for shorter mouse travel;
    if zigzag=False, all rows scan strictly top->bottom, left->right.
    Returns a list of (row, col, detect_box, click_box).
    """
    lx1, ly1, lx2, ly2 = clicking_areas["last_inventory_spot"]
    col3_cx = (lx1 + lx2) / 2.0
    row6_cy = (ly1 + ly2) / 2.0

    # At 1.0x baseline scale (360px wide side panel), slot pitch is 63px horizontal x 54px vertical
    step_x = 63.0 * ui_scale
    step_y = 54.0 * ui_scale
    detect_hw = max(12, int(round(detect_hw_base * ui_scale)))
    detect_hh = max(10, int(round(detect_hh_base * ui_scale)))
    click_hw = max(6, int(round(12 * ui_scale)))
    click_hh = max(6, int(round(11 * ui_scale)))

    slots = []
    for row in range(7):
        cols = (range(4) if (row % 2 == 0) else range(3, -1, -1)) if zigzag else range(4)
        for col in cols:
            cx = int(round(col3_cx - (3 - col) * step_x))
            cy = int(round(row6_cy - (6 - row) * step_y))
            detect_box = (
                max(0, cx - detect_hw),
                max(0, cy - detect_hh),
                cx + detect_hw,
                cy + detect_hh,
            )
            click_box = (
                max(0, cx - click_hw),
                max(0, cy - click_hh),
                cx + click_hw,
                cy + click_hh,
            )
            slots.append((row, col, detect_box, click_box))
    return slots


def is_slot_tagged_color(slot_bgr, style):
    """
    Detect if an inventory slot is tagged with RuneLite Inventory Tags for:
      - 'mage'  (Pure Blue #0000FF or Pure Cyan #00FFFF)
      - 'range' (Pure Green #00FF00)
      - 'melee' (Pure Red #FF0000)
      - 'spec'  (Pure Magenta / Pink #FF00FF)

    Why this never false-positives on untagged items (like Blighted Ice/Veng Sacks or potions):
    1. Every untagged OSRS item sprite is enclosed by a 1px pure-black silhouette border
       (RGB <= 15) where the item meets the brown inventory background (~BGR 38, 48, 55).
       RuneLite Inventory Tags replaces/tints that outer silhouette border with the tag color.
       So we check ONLY the outer silhouette border pixels adjacent to the inventory background,
       and reject any slot whose exterior silhouette border is still predominantly black.
    2. We require strict channel separation (suppressing Green for pure Blue so slate-blue
       Ice Sacks with G ~ 90-140 are ignored).
    """
    if slot_bgr is None or slot_bgr.size == 0:
        return False

    b = slot_bgr[:, :, 0].astype(np.int16)
    g = slot_bgr[:, :, 1].astype(np.int16)
    r = slot_bgr[:, :, 2].astype(np.int16)

    # 1. Locate the uniform brown OSRS inventory stone background (~BGR 38, 48, 55)
    bg_mask = (np.abs(b - 38) <= 14) & (np.abs(g - 48) <= 14) & (np.abs(r - 55) <= 14)
    # Dilate background by 2px so `exterior_border` captures the 1-2px outer silhouette of the item
    kernel = np.ones((5, 5), dtype=np.uint8)
    near_bg = cv2.dilate(bg_mask.astype(np.uint8), kernel, iterations=1) > 0
    exterior_border = near_bg & (~bg_mask)

    # Untagged items have a pure-black (R<=18, G<=18, B<=18) outer border touching the background
    black_border_pixels = int(np.count_nonzero(exterior_border & (r <= 18) & (g <= 18) & (b <= 18)))

    if style == "mage":
        # Pure Blue (#0000FF): high B, BOTH R and G suppressed (excludes slate-blue Ice Sack where G ~ 90-140)
        pure_blue = (b >= 195) & (r <= 45) & (g <= 50) & ((b - g) >= 145) & ((b - r) >= 150)
        # Pure Cyan (#00FFFF): both B and G very high, R suppressed
        pure_cyan = (b >= 210) & (g >= 210) & (r <= 35) & (np.abs(b - g) <= 25)
        # Blended Blue Fill on the exterior border (when using Fill with Blue #0000FF)
        fill_border = (b >= 115) & (r <= 45) & (g <= 45) & ((b - g) >= 75) & ((b - r) >= 75)
        tag_mask = pure_blue | pure_cyan
    elif style == "range":
        # Pure Green (#00FF00): high G, both R and B suppressed
        tag_mask = (g >= 195) & (r <= 45) & (b <= 45) & ((g - r) >= 150) & ((g - b) >= 150)
        fill_border = (g >= 115) & (r <= 45) & (b <= 45) & ((g - r) >= 75) & ((g - b) >= 75)
    elif style == "melee":
        # Pure Red (#FF0000): high R, both G and B suppressed
        tag_mask = (r >= 195) & (g <= 45) & (b <= 45) & ((r - g) >= 150) & ((r - b) >= 150)
        fill_border = (r >= 115) & (g <= 45) & (b <= 45) & ((r - g) >= 75) & ((r - b) >= 75)
    elif style == "spec":
        # Pure Magenta / Pink (#FF00FF): both R and B high, G suppressed, R and B balanced
        tag_mask = (
            (r >= 195) & (b >= 195) & (g <= 45)
            & ((r - g) >= 150) & ((b - g) >= 150)
            & (np.abs(r - b) <= 45)
        )
        fill_border = (
            (r >= 115) & (b >= 115) & (g <= 45)
            & ((r - g) >= 70) & ((b - g) >= 70)
            & (np.abs(r - b) <= 40)
        )
    else:
        return False

    # Count tag pixels lying directly on the item's exterior border touching the background
    border_tag_pixels = int(np.count_nonzero(exterior_border & (tag_mask | fill_border)))
    total_tag_pixels = int(np.count_nonzero(tag_mask))

    min_border_pixels = max(8, int(round(12 * ui_scale)))
    # A tagged item's outer silhouette has colored border pixels exceeding any stray black border pixels
    if border_tag_pixels >= min_border_pixels and border_tag_pixels > black_border_pixels:
        return True
    # Fallback if item fills almost the entire slot: require strong pure neon tag count and no black border
    if total_tag_pixels >= max(16, int(round(24 * (ui_scale ** 2)))) and black_border_pixels < min_border_pixels:
        return True
    return False


@timing_decorator
def equip_tagged_gear(style, append_first_spec=False):
    """
    Take a SINGLE screenshot of the 28-slot inventory grid, find all slots tagged with
    the requested style ('mage' = blue/cyan, 'range' = green, 'melee' = red), and click them rapidly.
    If append_first_spec=True, also scans top->bottom, left->right for the 1st 'spec' (Magenta #FF00FF)
    tagged item and clicks it LAST.
    Also uses the captured inventory screenshot in the background to refresh the combo-eat slot cache.
    """
    slots = get_inventory_slot_boxes(zigzag=True, detect_hw_base=27, detect_hh_base=25)
    ux1 = min(s[2][0] for s in slots)
    uy1 = min(s[2][1] for s in slots)
    ux2 = max(s[2][2] for s in slots)
    uy2 = max(s[2][3] for s in slots)

    shot = pyautogui.screenshot(region=(ux1, uy1, ux2 - ux1, uy2 - uy1))
    inv_bgr = cv2.cvtColor(np.array(shot), cv2.COLOR_RGB2BGR)

    # Refresh the combo-eat slot cache asynchronously using this inventory screenshot
    threading.Thread(
        target=update_combo_eat_cache_from_bgr,
        args=(inv_bgr.copy(), ux1, uy1),
        daemon=True,
    ).start()

    matched_slots = []
    for row, col, (dx1, dy1, dx2, dy2), click_box in get_inventory_slot_boxes(zigzag=True):
        slot_bgr = inv_bgr[dy1 - uy1:dy2 - uy1, dx1 - ux1:dx2 - ux1]
        if is_slot_tagged_color(slot_bgr, style):
            matched_slots.append((row, col, click_box))

    first_spec_slot = None
    if append_first_spec:
        # Scan strictly top->bottom (row 0..6), left->right (col 0..3) for the 1st Magenta ('spec') item
        for row, col, (dx1, dy1, dx2, dy2), click_box in get_inventory_slot_boxes(zigzag=False):
            slot_bgr = inv_bgr[dy1 - uy1:dy2 - uy1, dx1 - ux1:dx2 - ux1]
            if is_slot_tagged_color(slot_bgr, "spec"):
                first_spec_slot = (row, col, click_box)
                break
        if first_spec_slot is not None:
            matched_slots.append(first_spec_slot)

    for idx, (row, col, click_box) in enumerate(matched_slots):
        if idx > 0:
            time.sleep(random.uniform(0.012, 0.022))
        fast_click_spot(click_box)

    spec_info = f" + spec at {(first_spec_slot[0], first_spec_slot[1])}" if first_spec_slot else ""
    print(f"[Gear] Switched '{style}' gear{spec_info} ({len(matched_slots)} items clicked: {[(r, c) for r, c, _ in matched_slots]}).")
    return len(matched_slots)


def select_spell(spell_key="ice_barrage"):
    """Click the exact center of a calibrated spell slot ('ice_barrage' or 'blood_barrage') on the Magic tab."""
    if spell_key in ("ice_barrage", "blood_barrage") and isinstance(clicking_areas.get("ice_barrage"), tuple):
        ix1, iy1, ix2, iy2 = clicking_areas["ice_barrage"]
        # ice_barrage.png (34x37) has 3px left & 7px top background padding; true 29x29 icon center is (+17.5, +21.5)
        icx = ix1 + 17.5 * ui_scale if (iy2 - iy1) >= int(round(34 * ui_scale)) else (ix1 + ix2) / 2.0
        icy = iy1 + 21.5 * ui_scale if (iy2 - iy1) >= int(round(34 * ui_scale)) else (iy1 + iy2) / 2.0
        cx = icx - 72.0 * ui_scale if spell_key == "blood_barrage" else icx
        cy = icy
        r_half = max(3, int(round(5 * ui_scale)))
        box = (
            max(0, int(round(cx - r_half))),
            max(0, int(round(cy - r_half))),
            max(1, int(round(cx + r_half))),
            max(1, int(round(cy + r_half))),
        )
        if spell_key == "blood_barrage":
            clicking_areas["blood_barrage"] = box
    else:
        box = clicking_areas.get(spell_key)
    if isinstance(box, tuple) and len(box) == 4:
        fast_click_spot(box)
        print(f"[Magic] Selected spell '{spell_key}' at {box}.")
    elif spell_key in SPELL_TEMPLATES:
        find_and_click_image(SPELL_TEMPLATES[spell_key], searching_areas.get("magic_panel", searching_areas["inventory"]), fast=True)


@timing_decorator
def activate_spec_orb():
    """
    Check the Special Attack orb next to the minimap and click it ONLY if it is not yet activated.
    Compares 3-channel BGR template correlation against spec_orb_unactive.png vs spec_orb_active.png
    so the vivid cyan-blue unactive orb is cleanly distinguished from the glowing active orb.
    """
    unactive_tmpl = get_cached_template(SPEC_ORB_TEMPLATES["unactive"], color=True)
    active_tmpl = get_cached_template(SPEC_ORB_TEMPLATES["active"], color=True)
    if unactive_tmpl is None:
        fast_click_spot(clicking_areas["spec"])
        return True

    th, tw = unactive_tmpl.shape[:2]
    pad = max(4, int(round(6 * ui_scale)))
    sbox = searching_areas.get("spec")
    if not (isinstance(sbox, tuple) and len(sbox) == 4):
        bx1, by1, bx2, by2 = clicking_areas["spec"]
        sbox = (max(0, bx1 - pad), max(0, by1 - pad), bx2 + pad, by2 + pad)

    sx1, sy1, sx2, sy2 = sbox
    sx2 = max(sx2, sx1 + tw + 4)
    sy2 = max(sy2, sy1 + th + 4)

    shot = pyautogui.screenshot(region=(sx1, sy1, sx2 - sx1, sy2 - sy1))
    patch_bgr = cv2.cvtColor(np.array(shot), cv2.COLOR_RGB2BGR)

    res_unactive = cv2.matchTemplate(patch_bgr, unactive_tmpl, cv2.TM_CCOEFF_NORMED)
    _, unactive_val, _, unactive_loc = cv2.minMaxLoc(res_unactive)

    active_val = -1.0
    if active_tmpl is not None and patch_bgr.shape[0] >= active_tmpl.shape[0] and patch_bgr.shape[1] >= active_tmpl.shape[1]:
        res_active = cv2.matchTemplate(patch_bgr, active_tmpl, cv2.TM_CCOEFF_NORMED)
        _, active_val, _, _ = cv2.minMaxLoc(res_active)

    # If neither template matched strongly in searching_areas["spec"], rescan the minimap column once
    if max(unactive_val, active_val) < 0.72:
        full_shot = pyautogui.screenshot()
        full_bgr = cv2.cvtColor(np.array(full_shot), cv2.COLOR_RGB2BGR)
        full_gray = cv2.cvtColor(full_bgr, cv2.COLOR_BGR2GRAY)
        sh, sw = full_gray.shape[:2]
        pm_box = clicking_areas.get("prot_mage", BASELINE_CLICKING_AREAS["prot_mage"])
        if _calibrate_spec_orb_from_screen(full_gray, pm_box[0], pm_box[1], sw, sh):
            sx1, sy1, sx2, sy2 = searching_areas["spec"]
            sx2 = max(sx2, sx1 + tw + 4)
            sy2 = max(sy2, sy1 + th + 4)
            patch_bgr = full_bgr[sy1:sy2, sx1:sx2]
            if patch_bgr.shape[0] >= th and patch_bgr.shape[1] >= tw:
                _, unactive_val, _, unactive_loc = cv2.minMaxLoc(
                    cv2.matchTemplate(patch_bgr, unactive_tmpl, cv2.TM_CCOEFF_NORMED)
                )
                if active_tmpl is not None and patch_bgr.shape[0] >= active_tmpl.shape[0] and patch_bgr.shape[1] >= active_tmpl.shape[1]:
                    _, active_val, _, _ = cv2.minMaxLoc(
                        cv2.matchTemplate(patch_bgr, active_tmpl, cv2.TM_CCOEFF_NORMED)
                    )

    if active_val >= unactive_val and active_val >= 0.75:
        print(f"[Spec] Spec orb already active (active={active_val:.3f} >= unactive={unactive_val:.3f}) — skipping.")
        return False

    if unactive_val >= 0.72:
        inset_x = max(2, int(round(4 * ui_scale)))
        inset_y = max(2, int(round(4 * ui_scale)))
        matched_click_box = (
            sx1 + unactive_loc[0] + inset_x,
            sy1 + unactive_loc[1] + inset_y,
            sx1 + unactive_loc[0] + tw - inset_x,
            sy1 + unactive_loc[1] + th - inset_y,
        )
        clicking_areas["spec"] = matched_click_box
        fast_click_spot(matched_click_box)
        print(f"[Spec] Activated spec orb (unactive={unactive_val:.3f}, active={active_val:.3f}).")
        return True

    print(f"[Spec] Spec orb state uncertain (unactive={unactive_val:.3f}, active={active_val:.3f}) — clicking calibrated spec spot.")
    fast_click_spot(clicking_areas["spec"])
    return True


@timing_decorator
def on_f1_press(e):
    """F1: Swap to Mage gear (Blue/Cyan tag), activate Augury, select active barrage spell (Ice/Blood), and restore cursor."""
    global _combo_dwell_pause_until
    if e.event_type == keyboard.KEY_DOWN:
        _combo_dwell_pause_until = time.time() + 0.35
        orig_x, orig_y = pyautogui.position()

        # 1. Open Inventory and equip Mage gear
        fast_click_spot(clicking_areas["inventory_tag"])
        time.sleep(random.uniform(0.055, 0.07))
        equip_tagged_gear("mage")

        # 2. Open Prayer tab and activate Augury (if not already active)
        fast_click_spot(clicking_areas["prayer_tag"])
        time.sleep(random.uniform(0.065, 0.08))
        activate_prayers("augury")

        # 3. Open Magic tab and select active Barrage spell ('ice_barrage' or 'blood_barrage')
        fast_click_spot(clicking_areas["magic_tag"])
        time.sleep(random.uniform(0.055, 0.07))
        select_spell(active_barrage_spell)

        # 4. Return cursor to its original position so user can immediately click target
        pyautogui.moveTo(orig_x, orig_y, _pause=False)


def toggle_barrage_spell(e):
    """Toggle the spell selected by F1 between 'ice_barrage' and 'blood_barrage' on F12 press."""
    global active_barrage_spell
    if e.event_type == keyboard.KEY_DOWN:
        active_barrage_spell = (
            "blood_barrage" if active_barrage_spell == "ice_barrage" else "ice_barrage"
        )
        print(f"[Magic] F1 barrage spell toggled to '{active_barrage_spell}'.")


@timing_decorator
def on_f2_press(e):
    """F2: Swap to Range gear (Green tag), activate Rigour, return to Inventory tab, and restore cursor."""
    if e.event_type == keyboard.KEY_DOWN:
        orig_x, orig_y = pyautogui.position()

        # 1. Open Inventory and equip Range gear
        fast_click_spot(clicking_areas["inventory_tag"])
        time.sleep(random.uniform(0.055, 0.07))
        equip_tagged_gear("range")

        # 2. Open Prayer tab and activate Rigour (if not already active)
        fast_click_spot(clicking_areas["prayer_tag"])
        time.sleep(random.uniform(0.065, 0.08))
        activate_prayers("rigour")

        # 3. Return to Inventory tab and restore cursor to original position
        fast_click_spot(clicking_areas["inventory_tag"])
        pyautogui.moveTo(orig_x, orig_y, _pause=False)


@timing_decorator
def on_f3_press(e):
    """F3: Swap to Melee gear (Red tag), activate Piety, return to Inventory tab, and restore cursor."""
    if e.event_type == keyboard.KEY_DOWN:
        orig_x, orig_y = pyautogui.position()

        # 1. Open Inventory and equip Melee gear
        fast_click_spot(clicking_areas["inventory_tag"])
        time.sleep(random.uniform(0.055, 0.07))
        equip_tagged_gear("melee")

        # 2. Open Prayer tab and activate Piety (if not already active)
        fast_click_spot(clicking_areas["prayer_tag"])
        time.sleep(random.uniform(0.065, 0.08))
        activate_prayers("piety")

        # 3. Return to Inventory tab and restore cursor to original position
        fast_click_spot(clicking_areas["inventory_tag"])
        pyautogui.moveTo(orig_x, orig_y, _pause=False)


@timing_decorator
# @throttle
def on_f4_press(e):
    """
    F4: Swap to Melee gear (Red tag) + 1st Spec weapon (Magenta #FF00FF tag) last,
    activate Piety, return to Inventory tab, click Spec Orb last (if not already active),
    and restore cursor to its original position.
    """
    if e.event_type == keyboard.KEY_DOWN:
        orig_x, orig_y = pyautogui.position()

        # 1. Open Inventory, equip all Red melee gear, then click the 1st Magenta spec weapon (top->bottom, left->right) last
        fast_click_spot(clicking_areas["inventory_tag"])
        time.sleep(random.uniform(0.055, 0.07))
        equip_tagged_gear("melee", append_first_spec=True)

        # 2. Open Prayer tab and activate Piety (if not already active)
        fast_click_spot(clicking_areas["prayer_tag"])
        time.sleep(random.uniform(0.065, 0.08))
        activate_prayers("piety")

        # 3. Return to Inventory tab, activate Spec Orb last (if not already active), and restore cursor
        fast_click_spot(clicking_areas["inventory_tag"])
        activate_spec_orb()
        pyautogui.moveTo(orig_x, orig_y, _pause=False)


def is_prayer_active_glow(patch_bgr):
    """
    Check if an OSRS prayer slot already has the bright beige/yellow active glow behind the icon.
    Inactive prayer background is dark stone (~BGR 38, 48, 55); active glow is bright (~BGR 100, 185, 205).
    """
    b = patch_bgr[:, :, 0].astype(np.int16)
    g = patch_bgr[:, :, 1].astype(np.int16)
    r = patch_bgr[:, :, 2].astype(np.int16)
    glow_mask = (r >= 145) & (g >= 125) & ((r - b) >= 35)
    return float(np.mean(glow_mask)) >= 0.15


@timing_decorator
def activate_prayers(*prayer_keys):
    """
    Check and activate one or more prayers using a SINGLE screenshot for all of them.
    Skips any prayer that is already active (max_val <= 0.80) so it never toggles an active prayer OFF.
    """
    tasks = []
    pad = max(2, int(round(2 * ui_scale)))
    for pk in prayer_keys:
        anchor_crop_path = os.path.join(ANCHORS_DIR, f"{pk}.png")
        tmpl_path = anchor_crop_path if os.path.exists(anchor_crop_path) else PRAYER_TEMPLATES.get(pk)
        tmpl = get_cached_template(tmpl_path) if tmpl_path else None
        if tmpl is None:
            continue
        th, tw = tmpl.shape[:2]
        box = clicking_areas.get(pk)
        if isinstance(box, tuple) and len(box) == 4:
            x1, y1, x2, y2 = box
            sbox = searching_areas.get(pk, (max(0, x1 - pad), max(0, y1 - pad), x2 + pad, y2 + pad))
        else:
            sbox = searching_areas.get("prayer_panel", searching_areas["prayers"])
        sx1, sy1, sx2, sy2 = sbox
        sx2 = max(sx2, sx1 + tw + 2)
        sy2 = max(sy2, sy1 + th + 2)
        tasks.append((pk, tmpl, (sx1, sy1, sx2, sy2)))

    if not tasks:
        return

    # Grab ONE screenshot covering the bounding box of all requested prayers
    ux1 = min(t[2][0] for t in tasks)
    uy1 = min(t[2][1] for t in tasks)
    ux2 = max(t[2][2] for t in tasks)
    uy2 = max(t[2][3] for t in tasks)

    shot = pyautogui.screenshot(region=(ux1, uy1, ux2 - ux1, uy2 - uy1))
    union_gray = cv2.cvtColor(np.array(shot), cv2.COLOR_RGB2GRAY)

    clicked_any = False
    for pk, tmpl, (sx1, sy1, sx2, sy2) in tasks:
        sub_gray = union_gray[sy1 - uy1:sy2 - uy1, sx1 - ux1:sx2 - ux1]
        th, tw = tmpl.shape[:2]
        if sub_gray.shape[0] < th or sub_gray.shape[1] < tw:
            continue
        res = cv2.matchTemplate(sub_gray, tmpl, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(res)
        if max_val > 0.8:
            matched_box = (
                sx1 + max_loc[0],
                sy1 + max_loc[1],
                sx1 + max_loc[0] + tw,
                sy1 + max_loc[1] + th,
            )
            clicking_areas[pk] = matched_box
            if clicked_any:
                time.sleep(random.uniform(0.015, 0.025))
            fast_click_spot(matched_box)
            clicked_any = True
            print(f"[Prayer] Activated '{pk}' (max_val={max_val:.3f})")
        else:
            print(f"[Prayer] '{pk}' already active or not matched (max_val={max_val:.3f}) — skipping.")


def activate_prayer(prayer_key):
    activate_prayers(prayer_key)


@timing_decorator
# @throttle
def on_f5_press(e):
    global _combo_dwell_pause_until
    if e.event_type == keyboard.KEY_DOWN:
        _combo_dwell_pause_until = time.time() + 0.3
        fast_click_spot(clicking_areas["prayer_tag"])
        time.sleep(random.uniform(0.065, 0.08))
        activate_prayers("prot_mage", "augury")
        fast_click_spot(clicking_areas["inventory_tag"])


@timing_decorator
# @throttle
def on_f6_press(e):
    global _combo_dwell_pause_until
    if e.event_type == keyboard.KEY_DOWN:
        _combo_dwell_pause_until = time.time() + 0.3
        fast_click_spot(clicking_areas["prayer_tag"])
        time.sleep(random.uniform(0.065, 0.08))
        activate_prayers("prot_range")
        fast_click_spot(clicking_areas["inventory_tag"])


@timing_decorator
# @throttle
def on_f7_press(e):
    global _combo_dwell_pause_until
    if e.event_type == keyboard.KEY_DOWN:
        _combo_dwell_pause_until = time.time() + 0.3
        fast_click_spot(clicking_areas["prayer_tag"])
        time.sleep(random.uniform(0.065, 0.08))
        activate_prayers("prot_melee")
        fast_click_spot(clicking_areas["inventory_tag"])

# Pre-cached combo-eat queues updated in the background during inventory dwell time:
# Each entry is [row, col, click_box, item_name, remaining_doses]
_combo_cache_lock = Lock()
_combo_eat_cache = {
    "hard_food": [],
    "brew": [],
    "karambwan": [],
}
_combo_cache_initialized = False
_combo_dwell_pause_until = 0.0
_auto_eat_cooldown_until = 0.0
INVENTORY_DWELL_POLL_INTERVAL = 0.15  # Background scan interval (150ms) for HP bar + inventory dwell cache
AUTO_EAT_HP_THRESHOLD = 50.0          # Automatically combo-eat whenever HP falls below 50
AUTO_EAT_COOLDOWN = 1.25              # Seconds (~2 ticks) to wait after auto-eating before re-triggering

# Pre-cached Granite Maul inventory click box and F9 next-left-click arming state
_cached_gmaul_box = None
gmaul_armed = False
_gmaul_core_tmpl = None


def _get_gmaul_templates():
    """
    Load and cache both the BGR template and the binary foreground silhouette mask of granite_maul.png.
    The binary silhouette mask matches 100% identically whether the Granite Maul is highlighted
    (RuneLite Inventory Tags Outline/Fill of any color) or unhighlighted.
    """
    key = ("gmaul_tmpls", ui_scale)
    if key in _template_cache:
        return _template_cache[key]
    raw = cv2.imread(GMAUL_TEMPLATE_PATH, cv2.IMREAD_COLOR)
    if raw is None:
        return None
    trimmed = auto_trim_crop(raw, margin=2)
    if ui_scale != 1.0:
        th, tw = trimmed.shape[:2]
        rw = max(4, int(round(tw * ui_scale)))
        rh = max(4, int(round(th * ui_scale)))
        trimmed = cv2.resize(
            trimmed, (rw, rh), interpolation=cv2.INTER_AREA if ui_scale < 1.0 else cv2.INTER_LINEAR
        )
    # Build binary silhouette mask (1.0 for item pixels, 0.0 for brown inventory background)
    bg = trimmed[0, 0].astype(np.int16)
    diff = np.abs(trimmed.astype(np.int16) - bg).max(axis=2)
    sil_mask = (diff > 15).astype(np.float32)

    _template_cache[key] = (trimmed, sil_mask)
    return trimmed, sil_mask


def _find_gmaul_box_in_bgr(inv_bgr, ux1, uy1, threshold=0.80):
    """
    Locate the Granite Maul inside an inventory grid BGR image whether it is
    unhighlighted OR highlighted (tagged with RuneLite Inventory Tags Outline/Fill).
    """
    tmpls = _get_gmaul_templates()
    if tmpls is None or inv_bgr is None or inv_bgr.size == 0:
        return None
    bgr_tmpl, sil_tmpl = tmpls
    ih, iw = inv_bgr.shape[:2]
    th, tw = bgr_tmpl.shape[:2]
    if ih < th or iw < tw:
        return None

    # 1. Direct BGR template match (for unhighlighted Granite Maul)
    res_bgr = cv2.matchTemplate(inv_bgr, bgr_tmpl, cv2.TM_CCOEFF_NORMED)
    _, bgr_val, _, bgr_loc = cv2.minMaxLoc(res_bgr)

    # 2. Binary foreground silhouette match (matches highlighted/tagged Granite Maul of any color)
    b = inv_bgr[:, :, 0].astype(np.int16)
    g = inv_bgr[:, :, 1].astype(np.int16)
    r = inv_bgr[:, :, 2].astype(np.int16)
    inv_sil = ((np.abs(b - 41) > 15) | (np.abs(g - 53) > 15) | (np.abs(r - 62) > 15)).astype(np.float32)
    res_sil = cv2.matchTemplate(inv_sil, sil_tmpl, cv2.TM_CCOEFF_NORMED)
    _, sil_val, _, sil_loc = cv2.minMaxLoc(res_sil)

    if bgr_val >= threshold and bgr_val >= sil_val:
        best_loc = bgr_loc
    elif sil_val >= 0.82:
        best_loc = sil_loc
    else:
        return None

    cx = int(round(ux1 + best_loc[0] + tw / 2.0))
    cy = int(round(uy1 + best_loc[1] + th / 2.0))
    hw = max(5, int(round(8 * ui_scale)))
    hh = max(5, int(round(8 * ui_scale)))
    return (max(0, cx - hw), max(0, cy - hh), cx + hw, cy + hh)


def classify_combo_eat_slot(slot_bgr, threshold=0.82):
    """
    Classify a single inventory slot BGR patch into ('hard_food', 'brew', or 'karambwan').
    Uses yellow-liquid pre-filtering so brew vs non-brew templates never cross-check unnecessarily.
    Returns (category, item_name, doses, confidence) or None.
    """
    if slot_bgr is None or slot_bgr.size == 0:
        return None

    sh, sw = slot_bgr.shape[:2]
    b = slot_bgr[:, :, 0].astype(np.int16)
    g = slot_bgr[:, :, 1].astype(np.int16)
    r = slot_bgr[:, :, 2].astype(np.int16)

    # Fast skip for empty brown stone inventory slots (~BGR 41, 53, 62)
    fg_mask = (np.abs(b - 41) > 15) | (np.abs(g - 53) > 15) | (np.abs(r - 62) > 15)
    if int(np.count_nonzero(fg_mask)) < max(40, int(round(80 * (ui_scale ** 2)))):
        return None

    # Check if the slot has Saradomin brew bright yellow liquid
    yellow_mask = (r >= 155) & (g >= 155) & (b <= 110) & ((r - b) >= 65) & (np.abs(r - g) <= 40)
    min_yellow = max(35, int(round(90 * (ui_scale ** 2))))
    has_brew_yellow = int(np.count_nonzero(yellow_mask)) >= min_yellow

    candidate_categories = ("brew",) if has_brew_yellow else ("hard_food", "karambwan")

    best_cat = None
    best_name = None
    best_doses = 1
    best_val = -1.0

    for category in candidate_categories:
        for item_name, tmpl_path, doses in COMBO_FOOD_TEMPLATES.get(category, ()):
            tmpl = get_cached_template(tmpl_path, color=True)
            if tmpl is None:
                continue
            th, tw = tmpl.shape[:2]
            if sh < th or sw < tw:
                continue
            res = cv2.matchTemplate(slot_bgr, tmpl, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, _ = cv2.minMaxLoc(res)
            if max_val >= threshold and max_val > best_val:
                best_val = max_val
                best_cat = category
                best_name = item_name
                best_doses = doses

    if best_cat is not None:
        return best_cat, best_name, best_doses, best_val
    return None


def update_combo_eat_cache_from_bgr(inv_bgr, ux1, uy1):
    """
    Scan all 28 inventory slots from a captured inventory BGR image and update _combo_eat_cache
    as well as _cached_gmaul_box.
    If no food/brew/karambwan is visible (e.g. Prayer or Magic tab is currently open),
    preserves the existing cached inventory layout.
    """
    global _combo_cache_initialized, _cached_gmaul_box
    slots = get_inventory_slot_boxes(zigzag=False, detect_hw_base=27, detect_hh_base=25)
    new_queues = {"hard_food": [], "brew": [], "karambwan": []}
    total_found = 0

    for row, col, (dx1, dy1, dx2, dy2), click_box in slots:
        slot_bgr = inv_bgr[dy1 - uy1:dy2 - uy1, dx1 - ux1:dx2 - ux1]
        match = classify_combo_eat_slot(slot_bgr)
        if match is not None:
            cat, item_name, doses, _ = match
            new_queues[cat].append([row, col, click_box, item_name, doses])
            total_found += 1

    gmaul_box = _find_gmaul_box_in_bgr(inv_bgr, ux1, uy1)
    if gmaul_box is not None:
        with _combo_cache_lock:
            _cached_gmaul_box = gmaul_box

    if total_found > 0:
        with _combo_cache_lock:
            for cat in ("hard_food", "brew", "karambwan"):
                _combo_eat_cache[cat] = new_queues[cat]
            _combo_cache_initialized = True
    return total_found


def _get_hp_bar_box():
    """
    Return the (x1, y1, x2, y2) bounding box of the left-pillar RuneLite HP status bar,
    derived directly from clicking_areas['prot_mage'] (which is at offset (-87..-75, -174..+199)).
    """
    pm = clicking_areas.get("prot_mage")
    if isinstance(pm, tuple) and len(pm) == 4:
        ox, oy = pm[0], pm[1]
        return (
            max(0, int(round(ox - 87 * ui_scale))),
            max(0, int(round(oy - 174 * ui_scale))),
            max(1, int(round(ox - 75 * ui_scale))),
            max(1, int(round(oy + 199 * ui_scale))),
        )
    return searching_areas.get("hp_bar", (1801, 927, 1813, 1300))


def read_hp_from_bar(strip_bgr):
    """
    Estimate current HP (0.0..99.0) from the vertical RuneLite left-pillar HP status bar strip.
    Returns None if the status bar is not visible on screen (e.g. another window covers OSRS).
    """
    if strip_bgr is None or strip_bgr.size == 0:
        return None
    h, w = strip_bgr.shape[:2]
    if h < 40 or w < 4:
        return None

    b = strip_bgr[:, :, 0].astype(np.int16)
    g = strip_bgr[:, :, 1].astype(np.int16)
    r = strip_bgr[:, :, 2].astype(np.int16)

    # Filled HP row: bright red (R >= 90, R - B >= 50) or poison/venom green (G >= 75, G - B >= 35)
    filled_px = ((r >= 90) & ((r - b) >= 50)) | ((g >= 75) & ((g - b) >= 35))
    # Unfilled background row: dark charcoal (~BGR 20, 25, 29)
    unfilled_px = (r <= 48) & (g <= 48) & (b <= 48)

    # Inspect the lower 80% of the bar (below the heart icon and numeric digits, covering 0..79 HP)
    y_start = int(round(h * 0.20))
    lower_filled = filled_px[y_start:, :].mean(axis=1) >= 0.6
    lower_unfilled = unfilled_px[y_start:, :].mean(axis=1) >= 0.6

    # Validate that this strip is genuinely the OSRS status bar and player has > 0 HP
    if float(np.mean(lower_filled | lower_unfilled)) < 0.85 or not np.any(lower_filled[-8:]):
        return None

    unfilled_rows = np.where(~lower_filled)[0]
    if len(unfilled_rows) == 0:
        return 96.0
    first_filled_y = y_start + int(unfilled_rows[-1]) + 1
    filled_height = max(0, h - first_filled_y)
    return round(99.0 * filled_height / float(h), 1)


def refresh_combo_eat_cache_now(check_auto_eat=False):
    """
    Capture the left-pillar HP bar + 28-slot inventory region in a SINGLE screenshot,
    update the pre-cached combo-eat queues, and optionally return the current HP reading.
    """
    slots = get_inventory_slot_boxes(zigzag=False, detect_hw_base=27, detect_hh_base=25)
    inv_x1 = min(s[2][0] for s in slots)
    inv_y1 = min(s[2][1] for s in slots)
    inv_x2 = max(s[2][2] for s in slots)
    inv_y2 = max(s[2][3] for s in slots)

    hx1, hy1, hx2, hy2 = _get_hp_bar_box()
    ux1 = min(inv_x1, hx1) if check_auto_eat else inv_x1
    uy1 = min(inv_y1, hy1) if check_auto_eat else inv_y1
    ux2 = max(inv_x2, hx2) if check_auto_eat else inv_x2
    uy2 = max(inv_y2, hy2) if check_auto_eat else inv_y2

    shot = pyautogui.screenshot(region=(ux1, uy1, ux2 - ux1, uy2 - uy1))
    full_bgr = cv2.cvtColor(np.array(shot), cv2.COLOR_RGB2BGR)

    inv_bgr = full_bgr[inv_y1 - uy1:inv_y2 - uy1, inv_x1 - ux1:inv_x2 - ux1]
    update_combo_eat_cache_from_bgr(inv_bgr, inv_x1, inv_y1)

    if check_auto_eat:
        hp_strip = full_bgr[hy1 - uy1:hy2 - uy1, hx1 - ux1:hx2 - ux1]
        return read_hp_from_bar(hp_strip)
    return None


def inventory_dwell_watcher_loop():
    """
    Background daemon that:
      1. Keeps the next combo-eat slots (hard_food, brew, karambwan) and Granite Maul pre-cached
      2. Monitors the left-pillar RuneLite HP bar and automatically combo-eats when HP < 50
    """
    global _auto_eat_cooldown_until
    while True:
        try:
            now = time.time()
            if now >= _combo_dwell_pause_until:
                current_hp = refresh_combo_eat_cache_now(check_auto_eat=True)
                if (
                    current_hp is not None
                    and 0.0 < current_hp < AUTO_EAT_HP_THRESHOLD
                    and time.time() >= _auto_eat_cooldown_until
                ):
                    _auto_eat_cooldown_until = time.time() + AUTO_EAT_COOLDOWN
                    orig_x, orig_y = pyautogui.position()
                    print(f"[AutoEat] HP dropped to ~{current_hp:.0f} (< {AUTO_EAT_HP_THRESHOLD:.0f}) — triggering combo eat!")
                    combo_eat()
                    pyautogui.moveTo(orig_x, orig_y, _pause=False)
        except Exception:
            pass
        time.sleep(INVENTORY_DWELL_POLL_INTERVAL)


def _pop_next_cached_combo_targets():
    """
    Atomically pop the next (hard_food, brew, karambwan) click targets from _combo_eat_cache.
    Decrements brew dose count (4 -> 3 -> 2 -> 1 -> pop) so consecutive F8 presses stay accurate
    even before the next background dwell scan.
    """
    targets = []
    with _combo_cache_lock:
        for cat in ("hard_food", "brew", "karambwan"):
            queue = _combo_eat_cache.get(cat, [])
            if not queue:
                continue
            row, col, click_box, item_name, doses = queue[0]
            targets.append((cat, row, col, click_box, item_name))
            if cat == "brew" and doses > 1:
                queue[0][4] = doses - 1
            else:
                queue.pop(0)
    return targets


@timing_decorator
def combo_eat():
    """
    Perform a zero-screenshot 1-tick OSRS combo eat using the dwell-cached inventory slots:
      1. Click Inventory tab
      2. Click cached Standard/Heavy Food (Shark, Blighted Manta Ray, or Blighted Anglerfish)
      3. Click cached Saradomin Brew
      4. Click cached Karambwan
    """
    global _combo_dwell_pause_until
    # Pause background dwell scanner briefly while clicking + 1 tick (0.6s) so consumed slots update cleanly
    _combo_dwell_pause_until = time.time() + 0.65

    # Open Inventory tab immediately
    fast_click_spot(clicking_areas["inventory_tag"])

    # Fallback only if F8 is pressed before the background dwell scanner has ever seen the inventory
    if not _combo_cache_initialized:
        time.sleep(random.uniform(0.05, 0.065))
        refresh_combo_eat_cache_now()
    else:
        time.sleep(random.uniform(0.012, 0.02))

    targets = _pop_next_cached_combo_targets()

    clicked_items = []
    for idx, (cat, row, col, click_box, item_name) in enumerate(targets):
        if idx > 0:
            time.sleep(random.uniform(0.012, 0.02))
        fast_click_spot(click_box)
        clicked_items.append(f"{item_name}@({row},{col})")

    if clicked_items:
        print(f"[ComboEat] Ate {' -> '.join(clicked_items)}")
    else:
        print("[ComboEat] No cached food, brew, or karambwan remaining.")
    return len(clicked_items)


@timing_decorator
# @throttle
def on_f8_press(e):
    """F8: Perform 1-tick Combo Eat (Inventory -> Hard food -> Brew -> Karambwan) using pre-cached slots."""
    if e.event_type == keyboard.KEY_DOWN:
        orig_x, orig_y = pyautogui.position()
        combo_eat()
        pyautogui.moveTo(orig_x, orig_y, _pause=False)


def _is_point_in_ui_panel(x, y):
    """Return True if (x, y) is inside the right-hand inventory/side panel or minimap spec orb."""
    for area_key in ("inventory_panel", "magic_panel", "spec"):
        box = searching_areas.get(area_key)
        if isinstance(box, tuple) and len(box) == 4:
            if box[0] - 25 <= x <= box[2] + 25 and box[1] - 45 <= y <= box[3] + 45:
                return True
    return False


@timing_decorator
def execute_gmaul_spec(enemy_x, enemy_y):
    """
    Immediately equip the Granite Maul from inventory and click the Spec Orb,
    then restore cursor to (enemy_x, enemy_y).
    """
    global _combo_dwell_pause_until, _cached_gmaul_box
    _combo_dwell_pause_until = time.time() + 0.5

    with _combo_cache_lock:
        gmaul_box = _cached_gmaul_box

    # Fallback scan if Granite Maul wasn't cached yet
    if gmaul_box is None:
        slots = get_inventory_slot_boxes(zigzag=False, detect_hw_base=27, detect_hh_base=25)
        ux1 = min(s[2][0] for s in slots)
        uy1 = min(s[2][1] for s in slots)
        ux2 = max(s[2][2] for s in slots)
        uy2 = max(s[2][3] for s in slots)
        shot = pyautogui.screenshot(region=(ux1, uy1, ux2 - ux1, uy2 - uy1))
        inv_bgr = cv2.cvtColor(np.array(shot), cv2.COLOR_RGB2BGR)
        gmaul_box = _find_gmaul_box_in_bgr(inv_bgr, ux1, uy1)
        if gmaul_box is not None:
            with _combo_cache_lock:
                _cached_gmaul_box = gmaul_box

    if gmaul_box is None:
        print("[Gmaul] Granite Maul not found in inventory!")
        return False

    # 1. Click Granite Maul in inventory
    fast_click_spot(gmaul_box)
    time.sleep(random.uniform(0.015, 0.025))

    # 2. Click Spec Orb to fire the instant Gmaul special attack
    fast_click_spot(clicking_areas["spec"])

    # 3. Restore cursor back onto the enemy
    pyautogui.moveTo(enemy_x, enemy_y, _pause=False)
    print(f"[Gmaul] Equipped Granite Maul at {gmaul_box} -> clicked Spec Orb!")
    return True


# Delay (in seconds) after your left-click on the enemy before equipping Granite Maul + clicking Spec Orb.
# In OSRS, switching weapons on the same 0.6s tick as clicking the enemy cancels the queued AGS spec;
# waiting ~0.42-0.48s lets the AGS spec fire on the current tick and stacks the instant Gmaul spec on the next tick.
GMAUL_POST_CLICK_DELAY = (0.07, 0.08)


def _gmaul_next_click_worker():
    """
    Wait for the user's next left mouse click on the enemy (outside the inventory/spec UI panels),
    wait GMAUL_POST_CLICK_DELAY so the initial AGS spec registers on the current tick,
    then immediately trigger execute_gmaul_spec().
    """
    global gmaul_armed
    user32 = ctypes.windll.user32

    # Wait until any currently held left mouse button is released first
    while gmaul_armed and (user32.GetAsyncKeyState(0x01) & 0x8000):
        time.sleep(0.002)

    while gmaul_armed:
        if user32.GetAsyncKeyState(0x01) & 0x8000:
            click_x, click_y = pyautogui.position()
            # Wait for left button release so OSRS cleanly registers the user's click first
            while gmaul_armed and (user32.GetAsyncKeyState(0x01) & 0x8000):
                time.sleep(0.002)
            if not gmaul_armed:
                break
            # Ignore setup clicks inside the inventory panel or spec orb so only the click on the enemy triggers Gmaul
            if _is_point_in_ui_panel(click_x, click_y):
                continue
            gmaul_armed = False
            time.sleep(random.uniform(*GMAUL_POST_CLICK_DELAY))
            execute_gmaul_spec(click_x, click_y)
            break
        time.sleep(0.002)


def on_f9_press(e):
    """F9: Arm/disarm 1-tick AGS -> Granite Maul combo on next left click on enemy."""
    global gmaul_armed
    if e.event_type == keyboard.KEY_DOWN:
        if not gmaul_armed:
            gmaul_armed = True
            threading.Thread(target=refresh_combo_eat_cache_now, daemon=True).start()
            threading.Thread(target=_gmaul_next_click_worker, daemon=True).start()
            print(
                "[Gmaul] ARMED! Upon your next left-click on the enemy, script will click Granite Maul -> Spec Orb. "
                "(Press F9 again to cancel)"
            )
        else:
            gmaul_armed = False
            print("[Gmaul] DISARMED.")
    
def fast_click_spot(area):
    """Click a spot with minimal hover delay so OSRS registers the cursor position before clicking."""
    spot = weighted_random_point_in_area(area)
    pyautogui.moveTo(spot[0], spot[1], _pause=False)
    time.sleep(random.uniform(0.025, 0.035))
    pyautogui.click(spot[0], spot[1], _pause=False)


@timing_decorator
def emergency_teleport(source="manual"):
    """Interrupt any ongoing clicking, click inventory tab + teleport item, then enable Protect Item prayer."""
    global clicking
    clicking = False
    fast_click_spot(clicking_areas["inventory_tag"])
    time.sleep(random.uniform(0.02, 0.03))
    fast_click_spot(clicking_areas["last_inventory_spot"])

    # Switch to Prayer tab, wait for it to render, and enable Protect Item (only if not already active)
    time.sleep(random.uniform(0.03, 0.045))
    fast_click_spot(clicking_areas["prayer_tag"])
    time.sleep(random.uniform(0.065, 0.08))
    activate_prayers("prot_item")
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
def find_and_click_image(image_path, search_area, fast=False):
    start_time = time.time()
    
    # Read the template image first so we can ensure search_area is at least as large as template
    before_read_time = time.time()
    template = cv2.imread(image_path, 0)
    if template is None:
        print(f"Template image not found or unreadable: {image_path}")
        return False
    # Only rescale if not already using a freshly cropped anchor from ANCHORS_DIR
    if ui_scale != 1.0 and not str(image_path).startswith(ANCHORS_DIR):
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
    region_w = max(x_max - x_min, tw + 2)
    region_h = max(y_max - y_min, th + 2)

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

        if fast:
            pyautogui.moveTo(click_x, click_y, _pause=False)
            pre_click_time = time.time()
            pyautogui.click(click_x, click_y, _pause=False)
        else:
            # Move the mouse to the point (this initiates the hover)
            pyautogui.moveTo(click_x, click_y)
            
            # Wait for 0.05 seconds
            time.sleep(random.uniform(0.11, 0.125))

            pre_click_time = time.time()
            # Click on the weighted random point
            pyautogui.click(click_x, click_y)
        
        end_time = time.time()
        print(f"Image found and clicked in {(end_time - start_time) * 1000:.2f} ms. max_val is {max_val}. start-before = {before_read_time-start_time} imageread= {after_read_time-before_read_time} matchtime {match_time -after_read_time} click time = {end_time-pre_click_time} end-after {end_time-after_read_time}")
        return image_area
    else:
        print(f"Image not found (or prayer already active) in the search area, max value is {max_val:.3f}")
        return None

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


def wait_for_menu_and_calibrate():
    """
    Background startup task: if the script is launched while VSCode or another window is focused,
    poll lightly for the OSRS side-panel menu (tab stones) to appear on screen.
    As soon as you switch to the RuneLite screen, it clicks the Prayer tab and runs the full calibration.
    """
    global _combo_dwell_pause_until
    fast_scales = [ui_scale] if ui_scale == 1.0 else [ui_scale, 1.0]
    menu_anchors = [
        ("prayer_tag", os.path.join(ANCHORS_DIR, "prayer_tag.png")),
        ("inventory_tag", os.path.join(ANCHORS_DIR, "inventory_tag.png")),
        ("magic_tag", os.path.join(ANCHORS_DIR, "magic_tag.png")),
        ("prot_mage", "images/protect_from_mage.png"),
    ]
    loaded_tmpls = []
    for name, path in menu_anchors:
        if os.path.exists(path):
            t = cv2.imread(path, 0)
            if t is not None:
                loaded_tmpls.append((name, t))

    printed_waiting = False
    while True:
        screenshot_pil = pyautogui.screenshot()
        screen_gray = cv2.cvtColor(np.array(screenshot_pil), cv2.COLOR_RGB2GRAY)

        menu_visible = False
        for name, tmpl in loaded_tmpls:
            if match_template_multiscale(screen_gray, tmpl, scales=fast_scales, threshold=0.78) is not None:
                menu_visible = True
                break

        if menu_visible:
            # Pause background dwell scanner while initial calibration clicks Prayer & Magic tabs
            _combo_dwell_pause_until = time.time() + 1.5
            refresh_areas(open_prayer_tab=True)
            break

        if not printed_waiting:
            print("[Startup] Waiting for OSRS RuneLite menu on screen... (Switch to RuneLite window)")
            printed_waiting = True
        time.sleep(0.25)


# Load persisted areas if available
load_areas_config()

# Set up the listeners for F1-F12 and Esc keys immediately (zero startup delay)
keyboard.on_press_key("f1", on_f1_press)
keyboard.on_press_key("f2", on_f2_press)
keyboard.on_press_key("f3", on_f3_press)
keyboard.on_press_key("f4", on_f4_press)
keyboard.on_press_key("f5", on_f5_press)
keyboard.on_press_key("f6", on_f6_press)
keyboard.on_press_key("f7", on_f7_press)
keyboard.on_press_key("f8", on_f8_press)
keyboard.on_press_key("f9", on_f9_press)
keyboard.on_press_key("f10", on_f10_press)
keyboard.on_press_key("f11", toggle_alarm_watcher)
keyboard.on_press_key("f12", toggle_barrage_spell)
keyboard.on_press_key("esc", on_esc_press)
print("Listening for F1-F8, F9 (arm AGS->Gmaul on next click), Esc, F10 (refresh), F11 (PKer alarm), and F12 (Ice/Blood Barrage). Press Ctrl+C to exit.")

# Watch for RuneLite menu to appear on screen, then click Prayer tab and run full calibration
threading.Thread(target=wait_for_menu_and_calibrate, daemon=True).start()

# Start background inventory dwell watcher to pre-cache combo-eat slots and monitor HP bar
threading.Thread(target=inventory_dwell_watcher_loop, daemon=True).start()

# Keep the script running
keyboard.wait()

keyboard.wait()