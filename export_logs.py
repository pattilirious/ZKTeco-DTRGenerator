import csv
import calendar
import socket
import os
from concurrent.futures import ThreadPoolExecutor
from collections import defaultdict
from datetime import timedelta, date

DOUBLE_PUNCH_SECONDS = 30

CHECKIN_UNTIL = (11, 0)
CHECKOUT_FROM = (14, 30)   
BREAK_MID = (12, 30)       

LAST_IP_FILE = "last_ip.txt"
SLOT_NAMES = ["Check-in", "Break-out", "Break-in", "Check-out"]

def mins(dt):
    return dt.hour * 60 + dt.minute


def tmins(t):
    return t[0] * 60 + t[1]


def port_open(ip):
    try:
        with socket.create_connection((ip, 4370), timeout=0.5):
            return ip
    except OSError:
        return None


def ask_choice():
    while True:
        answer = input(
            "Which month to export? 1 = this month, 2 = last month, 3 = two months ago, ...\n"
            "Or type 'all' for the whole year: "
        ).strip().lower()
        if answer == "all":
            return "all"
        if answer.isdigit() and int(answer) >= 1:
            return int(answer)
        print("Please type a number like 1, 2 or 3, or the word all.")


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
        with open(LAST_IP_FILE) as f:
            last = f.read().strip()
        if last and port_open(last):
            return last
    subnet = my_subnet()
    print(f"Searching for the biometric on {subnet}.x ...")
    with ThreadPoolExecutor(max_workers=64) as ex:
        for found in ex.map(port_open, [f"{subnet}.{i}" for i in range(1, 255)]):
            if found:
                with open(LAST_IP_FILE, "w") as f:
                    f.write(found)
                return found
    raise SystemExit("Could not find the biometric on this network. "
                     "Check that the PC and device are on the same network.")


def fmt(dt):
    return dt.strftime("%I:%M").lstrip("0") if dt else ""


def dedupe(punches):
    """Drop accidental double punches (a few seconds apart) only."""
    kept = []
    for p in punches:
        if not kept or p - kept[-1] > timedelta(seconds=DOUBLE_PUNCH_SECONDS):
            kept.append(p)
    return kept


def assign(punches):
    rest = list(punches)
    check_in = break_out = break_in = check_out = None

    if rest and mins(rest[0]) < tmins(CHECKIN_UNTIL):
        check_in = rest.pop(0)
    if rest and mins(rest[-1]) >= tmins(CHECKOUT_FROM):
        check_out = rest.pop()

    if len(rest) >= 2:
        break_out, break_in = rest[0], rest[-1]
    elif len(rest) == 1:
        if mins(rest[0]) < tmins(BREAK_MID):
            break_out = rest[0]
        else:
            break_in = rest[0]

    return [check_in, break_out, break_in, check_out]


def remark(slots):
    if all(s is None for s in slots):
        return ""
    missing = [n for n, s in zip(SLOT_NAMES, slots) if s is None]
    return ("Missing: " + ", ".join(missing)) if missing else ""


def main():
    from zk import ZK

    choice = ask_choice()
    today = date.today()
    wanted = set()

    if choice == "all":
        for mo in range(1, today.month + 1):
            wanted.add((today.year, mo))
    else:
        y, m = today.year, today.month
        for _ in range(choice - 1):
            m -= 1
            if m == 0:
                m, y = 12, y - 1
        wanted.add((y, m))

    zk = ZK(find_device(), port=4370, timeout=10)
    conn = zk.connect()
    try:
        users = conn.get_users()
        names = {u.user_id: u.name for u in users}
        logs = conn.get_attendance()

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
                    w.writerow(["Day", "Weekday", "Check-in", "Break-out",
                                "Break-in", "Check-out", "Remarks"])
                    for d in range(1, days_in_month + 1):
                        weekday = date(year, month, d).strftime("%a")
                        punches = dedupe(sorted(data[(year, month)][name].get(d, [])))
                        slots = assign(punches)
                        w.writerow([d, weekday] + [fmt(p) for p in slots] + [remark(slots)])
                    w.writerow([])
                w.writerow([])

        print(f"Exported {len(data)} month(s) to attendance.csv")
    finally:
        conn.disconnect()

if __name__ == "__main__":
    main()