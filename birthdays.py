#!/usr/bin/env python3
import csv
import sys
import datetime

# Import from banner.py (must be in same directory or PYTHONPATH)
from banner import banner_lines, send_to_lpr

DEFAULT_CSV = "birthdays.csv"

def parse_date(date_str):
    """
    Parse common date formats; only month/day matter.
    """
    date_str = date_str.strip()
    fmts = [
        "%Y-%m-%d",
        "%m/%d/%Y",
        "%m/%d/%y",
        "%B %d, %Y",
        "%b %d, %Y",
        "%m-%d-%Y",
        "%m-%d-%y",
    ]
    for fmt in fmts:
        try:
            return datetime.datetime.strptime(date_str, fmt)
        except ValueError:
            pass
    return None

def preview(lines):
    pages = 1
    print("+" + "-"*80 + "+")
    for i, line in enumerate(lines, 1):
        print("|" + line + "|")
        if i % 66 == 0 and i != len(lines):
            print("+" + "-"*80 + "+\n" + "+" + "-"*80 + "+")
            pages += 1
    print("+" + "-"*80 + "+")
    print(f"{pages=}")

def main():
    csv_file = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_CSV

    today = datetime.date.today()
    today_month = today.month
    today_day = today.day

    try:
        with open(csv_file, newline='', encoding="utf-8") as f:
            reader = csv.DictReader(f)

            for row in reader:
                first = row.get("First Name", "").strip()
                alias = row.get("Alias", "").strip()
                dob_str = row.get("Date of Birth", "").strip()

                if not dob_str:
                    continue

                dob = parse_date(dob_str)
                if not dob:
                    continue

                if dob.month == today_month and dob.day == today_day:
                    name = alias if alias else first
                    if not name:
                        continue

                    message = f"Happy Birthday {name}!"

                    # Create banner text → returns list of strings
                    lines = banner_lines(message,
                                         page_lines=66,
                                         page_cols=80,
                                         rotate="cw",
                                         h_space=1,
                                         zoom=0,       # auto-zoom allowed
                                         #margin=5,
                                         #side_margin_cols=5
                                         )

                    # Print to default printer
                    if ("--preview" in sys.argv):
                        preview(lines)
                    elif ("--print" in sys.argv):
                        send_to_lpr(lines)
                        print(f"Printed birthday banner for: {name}")
                    else:
                        for line in lines:
                            print(line)
                    


    except FileNotFoundError:
        print(f"Error: Could not open file: {csv_file}")
        sys.exit(1)


if __name__ == "__main__":
    main()
