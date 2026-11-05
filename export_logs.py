from zk import ZK
import csv
import calendar
import socket
import os
from concurrent.futures import ThreadPoolExecutor
from collections import defaultdict
from datetime import timedelta, date
 
DOUBLE_PUNCH_MINUTES = 2
MONTHS_TO_EXPORT = 2  
BREAK_MID = (12, 30)
LAST_IP_FILE = "last_ip.txt"

def port_open(ip):
    try:
        with socket.create_connection((ip, 4370), timeout=0.5):
            return ip
    except OSError:
        return None

def my_subnet():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
    except OSError:
        ip = socket.gethostbyname(socket.gethostname())
    return ".".join(ip.split(".")[:3])

def find_device():
    if os.path.exists(LAST_IP_FILE):
        last = open(LAST_IP_FILE).read().strip()
        if last and port_open(last):
            return last
    subnet = my_subnet()
    print(f"Searching for the biometric on {subnet}.x ...")
    with ThreadPoolExecutor(max_workers=64) as ex:
        for found in ex.map(port_open, [f"{subnet}.{i}" for i in range(1, 255)]):
            if found:
                open(LAST_IP_FILE, "w").write(found)
                return found
    raise SystemExit("Could not find the biometric on this network. "
                     "Check that the PC and device are on the same network.")

def fmt(dt):
    return dt.strftime("%I:%M").lstrip("0") if dt else ""


def dedupe(punches):
    kept = []
    for p in punches:
        if not kept or p - kept[-1] > timedelta(minutes=DOUBLE_PUNCH_MINUTES):
            kept.append(p)
    return kept


def assign(punches):
    """Return [check_in, break_out, break_in, check_out]."""
    n = len(punches)
    if n == 0:
        return [None, None, None, None]
    if n == 1:
        p = punches[0]
        return [p, None, None, None] if p.hour < 12 else [None, None, None, p]
    if n == 2:
        return [punches[0], None, None, punches[1]]
    if n == 3:
        mid = punches[1]
        if (mid.hour, mid.minute) < BREAK_MID:
            return [punches[0], mid, None, punches[2]]
        return [punches[0], None, mid, punches[2]]
    return [punches[0], punches[1], punches[-2], punches[-1]]

wanted = set()
y, m = date.today().year, date.today().month
for _ in range(MONTHS_TO_EXPORT):
    wanted.add((y, m))
    m -= 1
    if m == 0:
        m, y = 12, y - 1

zk = ZK(find_device(), port=4370, timeout=10)
conn = zk.connect()
try:
    users = conn.get_users()
    names = {u.user_id: u.name for u in users}

    logs = conn.get_attendance()

    # (year, month) -> name -> day -> list of punches
    data = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    for a in logs:
        key = (a.timestamp.year, a.timestamp.month)
        if key not in wanted:
            continue
        name = names.get(a.user_id, f"Unknown ({a.user_id})")
        data[key][name][a.timestamp.day].append(a.timestamp)

    with open("attendance.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        for (year, month) in sorted(data):
            days_in_month = calendar.monthrange(year, month)[1]
            w.writerow([f"{calendar.month_name[month].upper()} {year}"])
            w.writerow([])
            for name in sorted(data[(year, month)]):
                w.writerow([name])
                w.writerow(["Day", "Weekday", "Check-in", "Break-out", "Break-in", "Check-out"])
                for d in range(1, days_in_month + 1):
                    weekday = date(year, month, d).strftime("%a")
                    punches = dedupe(sorted(data[(year, month)][name].get(d, [])))
                    w.writerow([d, weekday] + [fmt(p) for p in assign(punches)])
                w.writerow([])
            w.writerow([])

    print(f"Exported {len(data)} month(s) to attendance.csv")
finally:
    conn.disconnect()