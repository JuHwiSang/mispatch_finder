from pathlib import Path

def mark_by_dir(items, base_dir, marker):
    base = Path(base_dir).resolve()
    for item in items:
        # pytest 7/8 호환: 새 attr은 item.path(Path), 구버전은 item.fspath
        p = getattr(item, "path", None)
        p = Path(p) if p is not None else Path(str(getattr(item, "fspath")))
        try:
            p.resolve().relative_to(base)
        except ValueError:
            continue
        item.add_marker(marker)  # 런타임에 마커 추가 가능
