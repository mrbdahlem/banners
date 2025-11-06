Here is a clean **project README** (neutral, instructional tone — not the playful persona):

---

# Birthday Banner Printer

This project generates **sideways dot-matrix style banners** on a classic 80×66 text page format using a custom ASCII banner renderer.
It includes two main components:

* `banner.py` — renders large sideways ASCII text banners.
* `birthdays.py` — checks a CSV for birthdays and prints (or previews) birthday banners.

---

## Requirements

* Python 3.7+
* A system capable of printing text via `lpr` **(optional)**
  (Linux / macOS / Windows with CUPS or equivalent)

---

## Files

| File            | Description                                                             |
| --------------- | ----------------------------------------------------------------------- |
| `banner.py`     | Renders banner text, handles rotation, centering, scaling, and printing |
| `birthdays.py`  | Reads a birthday CSV and prints or previews birthday messages           |
| `birthdays.csv` | User-provided CSV of names and birthdays                                |

---

## `birthdays.csv` Format

The CSV must contain the following columns:

| Column            | Meaning                                                |
| ----------------- | ------------------------------------------------------ |
| **First Name**    | Person's given name                                    |
| **Alias**         | Optional display name (used if present)                |
| **Date of Birth** | Date in a common format (YYYY-MM-DD, MM/DD/YYYY, etc.) |

Example:

```
First Name,Alias,Date of Birth
Alice,Ally,2005-03-05
Brian,,03/05/2002
Charlotte,Charlie,March 5, 2007
```

If today matches the **month and day** of the birthday, a banner is generated.

---

## Usage: `birthdays.py`

```bash
python3 birthdays.py
```

Defaults to reading `birthdays.csv`.

### Specify another CSV:

```bash
python3 birthdays.py staff_birthdays.csv
```

### Output Modes

| Flag                     | Output Behavior                                                          |
| ------------------------ | ------------------------------------------------------------------------ |
| *(no flag)*              | Writes banner text to **stdout** (recommended for redirecting to a file) |
| `--preview`              | Prints the banner to the terminal for viewing                            |
| `--print` or `--printer` | Sends the banner to the default system printer via `lpr`                 |

#### Examples

Preview banners on screen:

```bash
python3 birthdays.py --preview
```

Send banners directly to the printer:

```bash
python3 birthdays.py --print
```

Redirect banner output to a file:

```bash
python3 birthdays.py > today_banner.txt
```

---

## Usage: `banner.py` (Standalone)

Render and preview a banner:

```bash
python3 banner.py "HELLO WORLD" --preview
```

Send directly to printer:

```bash
python3 banner.py "HELLO WORLD" --print
```

---

## How the Banner Works

* Letters are drawn using a **5×7 bitmap font**.
* The text is **scaled** by an integer zoom factor.
* The banner is **rotated 90°** so it prints sideways across the page.
* Output is **centered** across:

  * Page width (default 80 columns)
  * Page height (default 66 lines, including automatic top/bottom padding)

The default sizing automatically attempts to:

* Maximize letter height
* Maintain a top/bottom margin (~10 lines)
* Maintain side margins (~5 columns)
* Fit cleanly into page width

---

## Scheduling (Optional)

To print banners automatically each morning:

**Linux / macOS (`cron`):**

```bash
crontab -e
```

Add:

```
0 7 * * * /usr/bin/python3 /path/to/birthdays.py --print
```

---

## License

MIT License
