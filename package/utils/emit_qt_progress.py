def emit_qt_progress(current: int, total: int, desc: str):
    desc_clean = (desc or "").replace("\n", " ").strip()
    print(f"[QT_PROGRESS] current={current} total={total} desc={desc_clean}", flush=True)

def emit_qt_info(message: str):
    msg = (message or "").replace("\n", " ").strip()
    print(f"[QT_INFO] {msg}", flush=True)