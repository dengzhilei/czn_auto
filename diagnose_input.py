from __future__ import annotations

import ctypes
import argparse
import os
from ctypes import wintypes

import czn_detector
from czn_detector import click_area_for, describe_window_at, message_target_at, set_dpi_awareness, window_at

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
advapi32 = ctypes.WinDLL("advapi32", use_last_error=True)
user32 = ctypes.WinDLL("user32", use_last_error=True)

advapi32.GetSidSubAuthorityCount.argtypes = [ctypes.c_void_p]
advapi32.GetSidSubAuthorityCount.restype = ctypes.POINTER(ctypes.c_ubyte)
advapi32.GetSidSubAuthority.argtypes = [ctypes.c_void_p, wintypes.DWORD]
advapi32.GetSidSubAuthority.restype = ctypes.POINTER(wintypes.DWORD)


PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
TOKEN_QUERY = 0x0008
TokenIntegrityLevel = 25

WM_MOUSEMOVE = 0x0200
WM_LBUTTONDOWN = 0x0201
WM_LBUTTONUP = 0x0202
WM_ACTIVATE = 0x0006
WA_ACTIVE = 1
MK_LBUTTON = 0x0001


class SID_AND_ATTRIBUTES(ctypes.Structure):
    _fields_ = (("Sid", ctypes.c_void_p), ("Attributes", wintypes.DWORD))


class TOKEN_MANDATORY_LABEL(ctypes.Structure):
    _fields_ = (("Label", SID_AND_ATTRIBUTES),)


class POINT(ctypes.Structure):
    _fields_ = (("x", ctypes.c_long), ("y", ctypes.c_long))


def is_admin() -> bool:
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def integrity_name(rid: int | None) -> str:
    if rid is None:
        return "unknown"
    if rid >= 0x4000:
        return f"system({rid})"
    if rid >= 0x3000:
        return f"high({rid})"
    if rid >= 0x2000:
        return f"medium({rid})"
    if rid >= 0x1000:
        return f"low({rid})"
    return f"untrusted({rid})"


def process_integrity(pid: int) -> tuple[int | None, str]:
    hwnd_proc = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not hwnd_proc:
        return None, f"OpenProcess failed err={ctypes.get_last_error()}"
    token = wintypes.HANDLE()
    if not advapi32.OpenProcessToken(hwnd_proc, TOKEN_QUERY, ctypes.byref(token)):
        err = ctypes.get_last_error()
        kernel32.CloseHandle(hwnd_proc)
        return None, f"OpenProcessToken failed err={err}"
    needed = wintypes.DWORD()
    advapi32.GetTokenInformation(token, TokenIntegrityLevel, None, 0, ctypes.byref(needed))
    buf = ctypes.create_string_buffer(needed.value)
    if not advapi32.GetTokenInformation(token, TokenIntegrityLevel, buf, needed, ctypes.byref(needed)):
        err = ctypes.get_last_error()
        kernel32.CloseHandle(token)
        kernel32.CloseHandle(hwnd_proc)
        return None, f"GetTokenInformation failed err={err}"
    label = ctypes.cast(buf, ctypes.POINTER(TOKEN_MANDATORY_LABEL)).contents
    sub_count = advapi32.GetSidSubAuthorityCount(label.Label.Sid).contents.value
    rid = advapi32.GetSidSubAuthority(label.Label.Sid, sub_count - 1).contents.value
    kernel32.CloseHandle(token)
    kernel32.CloseHandle(hwnd_proc)
    return int(rid), "ok"


def foreground_info() -> str:
    hwnd = user32.GetForegroundWindow()
    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    title = ctypes.create_unicode_buffer(256)
    user32.GetWindowTextW(hwnd, title, 256)
    return f"hwnd=0x{hwnd:x} pid={pid.value} title={title.value!r}"


def monitor_for_point(x: int, y: int) -> dict:
    import mss

    mss_cls = getattr(mss, "MSS", None) or getattr(mss, "mss")
    with mss_cls() as sct:
        for monitor in sct.monitors[1:]:
            if (
                monitor["left"] <= x < monitor["left"] + monitor["width"]
                and monitor["top"] <= y < monitor["top"] + monitor["height"]
            ):
                return dict(monitor)
        return dict(sct.monitors[0])


def post_message_probe(hwnd: int, x: int, y: int) -> list[str]:
    client = POINT(x, y)
    user32.ScreenToClient(hwnd, ctypes.byref(client))
    lparam = ((client.y & 0xFFFF) << 16) | (client.x & 0xFFFF)
    out = [f"client_point=({client.x},{client.y}) lparam=0x{lparam:x}"]
    for msg, wp in ((WM_MOUSEMOVE, 0), (WM_LBUTTONDOWN, MK_LBUTTON), (WM_LBUTTONUP, 0)):
        ctypes.set_last_error(0)
        ok = user32.PostMessageW(hwnd, msg, wp, lparam)
        out.append(f"PostMessage {hex(msg)} ok={ok} err={ctypes.get_last_error()}")
    return out


def target_candidates(hwnd: int) -> list[tuple[str, int]]:
    root = int(user32.GetAncestor(hwnd, 3)) or hwnd
    popup = int(user32.GetLastActivePopup(root)) or root
    candidates = [("window_at_point", hwnd), ("root_owner", root), ("active_popup", popup)]
    deduped: list[tuple[str, int]] = []
    seen: set[int] = set()
    for label, target in candidates:
        if target and target not in seen:
            deduped.append((label, target))
            seen.add(target)
    return deduped


def window_title(hwnd: int) -> str:
    title = ctypes.create_unicode_buffer(256)
    user32.GetWindowTextW(hwnd, title, 256)
    return title.value


def probe_candidate(label: str, hwnd: int, x: int, y: int, activate: bool, dry_run: bool) -> None:
    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    print(f"[{label}] hwnd=0x{hwnd:x} pid={pid.value} title={window_title(hwnd)!r}")
    client = POINT(x, y)
    user32.ScreenToClient(hwnd, ctypes.byref(client))
    print(f"client_point=({client.x},{client.y})")
    if dry_run:
        print("dry_run=true; no mouse messages sent")
        return
    if activate:
        ctypes.set_last_error(0)
        ok = user32.PostMessageW(hwnd, WM_ACTIVATE, WA_ACTIVE, 0)
        print(f"PostMessage WM_ACTIVATE ok={ok} err={ctypes.get_last_error()}")
    for line in post_message_probe(hwnd, x, y):
        print(line)


def main() -> None:
    parser = argparse.ArgumentParser(description="Probe whether a window accepts background mouse messages.")
    parser.add_argument("--x", type=int, default=3590, help="Screen x coordinate to click/probe.")
    parser.add_argument("--y", type=int, default=1885, help="Screen y coordinate to click/probe.")
    parser.add_argument("--activate", action="store_true", help="Also send WM_ACTIVATE before mouse messages.")
    parser.add_argument(
        "--target-window-title",
        default="",
        help="Prefer a visible window whose title contains this text.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Resolve targets without sending mouse messages.")
    args = parser.parse_args()

    set_dpi_awareness()
    czn_detector.INPUT_TARGET_WINDOW_TITLE = args.target_window_title.strip()
    x, y = args.x, args.y
    hwnd = window_at(x, y)
    pid = wintypes.DWORD()
    ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    own_pid = os.getpid()
    own_rid, own_status = process_integrity(own_pid)
    target_rid, target_status = process_integrity(pid.value)

    print(f"self_pid={own_pid} admin={is_admin()} integrity={integrity_name(own_rid)} status={own_status}")
    print(f"target_at=({x},{y}) {describe_window_at(x, y)}")
    print(f"target_integrity={integrity_name(target_rid)} status={target_status}")
    print(f"foreground={foreground_info()}")
    print(f"click_area={click_area_for(monitor_for_point(x, y))}")
    if czn_detector.INPUT_TARGET_WINDOW_TITLE:
        target = message_target_at(x, y)
        if target:
            probe_candidate("configured_title", target, x, y, args.activate, args.dry_run)
        else:
            print(f"configured_title target not found: {czn_detector.INPUT_TARGET_WINDOW_TITLE!r}")
    else:
        for label, target in target_candidates(hwnd):
            probe_candidate(label, target, x, y, args.activate, args.dry_run)


if __name__ == "__main__":
    main()
