import os

# ==========================================
# CẤU HÌNH PROFILE VÀ ĐƯỜNG DẪN TRÌNH DUYỆT
# ==========================================

# 1. Thư mục chứa dữ liệu người dùng của Edge
# Edge mới yêu cầu thư mục dữ liệu riêng để Selenium có thể kết nối DevTools.
EDGE_USER_DATA_DIR = os.path.expanduser("~/.config/ms-bot-edge")

# Tự nhận profile Edge thực tế, kể cả profile chưa được nhập vào dữ liệu bot.
from core.edge_profiles import discover_profiles, profile_labels

EDGE_SOURCE_USER_DATA_DIR = os.path.expanduser("~/.config/microsoft-edge")
PROFILES_LIST = discover_profiles(EDGE_USER_DATA_DIR, EDGE_SOURCE_USER_DATA_DIR)
PROFILE_LABELS = profile_labels(EDGE_USER_DATA_DIR, EDGE_SOURCE_USER_DATA_DIR)

# Khai báo Email tương ứng với từng Profile để chuyển đổi trên Waydroid
WAYDROID_EMAILS = {
    "Profile 2": "tiktokpromaxlayer2@gmail.com",
    "Profile 4": "tiktokpromaxlayer@gmail.com",
    "Profile 5": "diemthuy6993@gmail.com",
}

# 3. Đường dẫn Binary và Driver
MS_EDGE_BINARY = "/usr/bin/microsoft-edge"
DRIVER_FILENAME = "msedgedriver"
PROGRESS_FILE = "bot_progress.json"

# ==========================================
# CƠ SỞ DỮ LIỆU TỪ KHÓA TÌM KIẾM
# ==========================================
WORD_LIST = [
    # 2-3 Letters
    "ai", "api", "app", "arc", "art", "bin", "bit", "bot", "box", "bus",
    "cap", "cpu", "dat", "dev", "doc", "env", "eye", "fan", "fun", "gas",
    "git", "gpu", "gui", "hub", "id", "io", "ip", "job", "joy", "key",
    "kit", "lab", "lan", "lib", "log", "mac", "map", "max", "mix", "net",
    "new", "now", "npm", "ops", "os", "pad", "pay", "pc", "pen", "pin",
    "pod", "pop", "pro", "ram", "raw", "run", "sdk", "set", "sky", "src",
    "ssh", "ssl", "sub", "sun", "sys", "tab", "tag", "tap", "tcp", "tip",
    "top", "toy", "ui", "usb", "use", "ux", "van", "vip", "vm", "vpn",
    "vps", "web", "win", "zen", "zip",

    # 4 Letters
    "area", "auto", "back", "bank", "base", "beat", "beta", "bias", "bios",
    "blob", "blue", "body", "book", "boot", "boss", "byte", "cafe", "card",
    "cash", "cell", "chat", "chip", "city", "club", "code", "coin", "cool",
    "core", "crew", "cube", "dark", "dash", "data", "date", "deal", "deck",
    "deep", "demo", "desk", "disk", "docs", "door", "draw", "drop", "dual",
    "dust", "easy", "edge", "edit", "face", "fast", "feed", "file", "film",
    "fire", "fish", "flag", "flat", "flow", "flux", "font", "form", "free",
    "fuel", "full", "fund", "game", "gate", "gear", "gift", "gold", "good",
    "grid", "guru", "hack", "hard", "hash", "head", "heap", "help", "hero",
    "hint", "home", "host", "icon", "idea", "info", "item", "java", "jump",
    "kick", "king", "lab", "lamp", "land", "life", "line", "link", "list",
    "live", "load", "lock", "loop", "love", "mail", "main", "make", "mark",
    "mask", "math", "mega", "menu", "mesh", "meta", "mind", "mini", "mode",
    "moon", "move", "name", "nano", "neon", "news", "next", "node", "note",
    "nova", "open", "pack", "page", "pair", "park", "part", "pass", "path",
    "plan", "play", "plug", "plus", "pool", "port", "post", "push", "rack",
    "raid", "rank", "rate", "read", "real", "rich", "road", "role", "room",
    "root", "ruby", "rule", "rust", "safe", "sale", "save", "scan", "seed",
    "shop", "show", "side", "site", "size", "skin", "skip", "slug", "snap",
    "soft", "solo", "song", "sort", "soul", "spam", "spec", "spin", "spot",
    "star", "stat", "step", "stop", "sync", "tags", "talk", "tank", "task",
    "team", "tech", "term", "test", "text", "time", "tool", "tour", "town",
    "tree", "type", "unit", "unix", "user", "view", "wall", "wave", "wiki",
    "wild", "wind", "wire", "word", "work", "zone", "zoom",

    # 5-6 Letters
    "access", "action", "active", "actor", "admin", "agent", "alert",
    "alpha", "anchor", "apple", "array", "asset", "atlas", "audio", "audit",
    "badge", "basic", "batch", "beach", "block", "board", "boost", "brain",
    "brand", "brick", "bridge", "brief", "broad", "broker", "build", "burst",
    "buyer", "cable", "cache", "camera", "canvas", "cargo", "center", "chain",
    "chair", "chart", "check", "chief", "circle", "civic", "claim", "class",
    "clean", "clear", "click", "client", "clock", "clone", "cloud", "coach",
    "coast", "code", "color", "comic", "common", "config", "const", "control",
    "cookie", "count", "cover", "craft", "crash", "crate", "credit", "cross",
    "crowd", "crypt", "curve", "cycle", "daily", "dance", "data", "debug",
    "delta", "depth", "design", "device", "digit", "direct", "docker", "domain",
    "draft", "drain", "dream", "drive", "drone", "eagle", "earth", "editor",
    "effect", "elite", "email", "energy", "engine", "entry", "equal", "event",
    "extra", "factor", "field", "fight", "final", "first", "flash", "fleet",
    "float", "floor", "fluid", "focus", "folder", "force", "forest", "forge",
    "format", "forum", "frame", "fresh", "front", "fruit", "future", "gadget",
    "galaxy", "garage", "garden", "gauge", "genius", "ghost", "giant", "glass",
    "global", "globe", "glory", "grade", "grand", "graph", "grass", "green",
    "grid", "gross", "ground", "group", "guard", "guest", "guide", "guild",
    "habit", "happy", "heart", "heavy", "hello", "hobby", "hotel", "house",
    "human", "hybrid", "hyper", "image", "impact", "import", "index", "input",
    "inside", "issue", "item", "joint", "juice", "label", "laser", "launch",
    "layer", "layout", "leader", "lease", "legal", "level", "light", "limit",
    "linux", "local", "logic", "login", "magic", "magnet", "major", "maker",
    "manage", "manual", "market", "master", "match", "matrix", "media", "medal",
    "member", "memory", "mental", "metal", "meter", "method", "metric", "micro",
    "might", "minor", "mixer", "mobile", "model", "modern", "module", "money",
    "motion", "motor", "mount", "mouse", "movie", "music", "native", "nature",
    "night", "noble", "noise", "north", "novel", "number", "nurse", "object",
    "ocean", "office", "offset", "option", "orbit", "order", "origin", "outlet",
    "output", "owner", "packet", "panel", "paper", "param", "party", "patch",
    "patrol", "peace", "phase", "phone", "photo", "pilot", "pixel", "place",
    "plain", "plane", "planet", "plant", "plate", "player", "point", "polar",
    "policy", "portal", "poster", "power", "press", "price", "prime", "print",
    "prize", "probe", "profit", "promo", "prompt", "proof", "proto", "proxy",
    "public", "pulse", "punch", "pupil", "query", "quest", "queue", "quick",
    "quote", "radar", "radio", "radius", "rally", "ranch", "random", "range",
    "rapid", "ratio", "reach", "react", "realm", "record", "region", "relay",
    "remote", "render", "repair", "replay", "report", "reset", "result", "retro",
    "review", "reward", "rider", "right", "rival", "river", "robot", "rocket",
    "roller", "round", "route", "router", "royal", "rule", "rural", "safety",
    "salad", "sample", "scale", "scene", "school", "scope", "score", "screen",
    "script", "search", "secret", "sector", "secure", "select", "sense", "sensor",
    "series", "server", "setup", "shade", "shadow", "shape", "share", "shark",
    "sharp", "sheet", "shell", "shield", "shift", "shirt", "shock", "shoot",
    "shop", "shore", "short", "sight", "signal", "silent", "silver", "simple",
    "single", "skill", "skull", "slate", "slice", "slide", "smart", "smile",
    "smoke", "snake", "social", "socket", "solar", "solid", "sonic", "sound",
    "source", "south", "space", "spark", "speak", "speed", "sphere", "spice",
    "spider", "spike", "spine", "spirit", "split", "sport", "spot", "spray",
    "spread", "spring", "sprint", "sprite", "squad", "square", "stable", "stack",
    "staff", "stage", "stamp", "stand", "star", "start", "state", "static",
    "stats", "status", "steam", "steel", "stick", "stock", "stone", "store",
    "storm", "story", "stream", "street", "stress", "strike", "string", "strip",
    "strong", "studio", "study", "stuff", "style", "sugar", "suite", "summer",
    "summit", "super", "supply", "surge", "switch", "symbol", "system", "table",
    "tablet", "tag", "talent", "target", "taste", "teach", "team", "tempo",
    "tennis", "term", "test", "theme", "theory", "thing", "thread", "ticket",
    "tiger", "tile", "timer", "title", "toast", "token", "tonic", "tool",
    "topic", "torch", "total", "touch", "tower", "town", "toy", "trace",
    "track", "trade", "trail", "train", "trait", "travel", "treat", "trend",
    "trial", "tribe", "trick", "trip", "troop", "truck", "trunk", "trust",
    "truth", "tunnel", "turbo", "type", "ultra", "uncle", "union", "unity",
    "update", "upper", "urban", "usage", "user", "valid", "valley", "value",
    "valve", "vapor", "vault", "vector", "venue", "verify", "video", "view",
    "vinyl", "virus", "vision", "visit", "visual", "vital", "vocal", "voice",
    "volume", "vote", "voyage", "wagon", "wait", "walk", "wallet", "watch",
    "water", "wave", "wealth", "weapon", "web", "weight", "weird", "whale",
    "wheat", "wheel", "white", "whole", "widget", "width", "wild", "window",
    "wing", "winner", "winter", "wire", "wisdom", "wise", "wish", "wit",
    "wolf", "wonder", "wood", "wool", "word", "work", "world", "worth",
    "wrap", "wrist", "write", "writer", "yard", "year", "yellow", "yield",
    "yoga", "young", "youth", "zebra", "zero", "zone", "zoom"
]
# ==========================================
# CẤU HÌNH WAYDROID & ADB
# ==========================================
WAYDROID_IP = "192.168.240.112:5555"
WAYDROID_PROGRESS_FILE = "waydroid_progress.json"
BING_APP_PACKAGE = "com.microsoft.bing"
# ==========================================
# THÔNG SỐ RUNTIME MẶC ĐỊNH
# ==========================================
DEFAULT_BOT_CONFIG = {
    "pc_count": 35,
    "mobile_count": 25,
    "check_interval": 3,
    "type_min": 0.3,
    "type_max": 0.3,
    "read_min": 3,
    "read_max": 4,
    "think_time": 3,
}

PROFILE_SWITCH_DELAY = 10
CAPTCHA_WAIT_SECONDS = 90
SHUTDOWN_COUNTDOWN_SECONDS = 60
WAYDROID_NEWS_COUNT = 15
WAYDROID_CHECKIN_X = [0.125, 0.243, 0.375, 0.500, 0.628, 0.754, 0.885]
WAYDROID_CHECKIN_Y = 0.539

# Timeout kỹ thuật: không thay đổi logic tác vụ, chỉ ngăn tiến trình treo vô hạn.
ADB_COMMAND_TIMEOUT = 12
PAGE_LOAD_TIMEOUT = 45
DRIVER_RETRY_COUNT = 2

# Browser parameters preserved from v5.2.
REMOTE_DEBUGGING_PORT = 9222
MOBILE_WINDOW_SIZE = "390,844"
MOBILE_USER_AGENT = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 "
    "Mobile/15E148 Safari/604.1"
)
MOBILE_PLATFORM = "iPhone"
MOBILE_ACCEPT_LANGUAGE = "vi-VN,vi;q=0.9,en-US;q=0.8"
MOBILE_PLATFORM_VERSION = "16.6"
