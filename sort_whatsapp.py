import sys
import re
import shutil
from pathlib import Path
from datetime import datetime

# Extensions to sort
ALLOWED_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".gif", ".webp", ".heic",
    ".mp4", ".mov", ".avi", ".mkv", ".3gp",
    ".mp3", ".m4a", ".aac", ".opus",
    ".pdf", ".doc", ".docx"
}

OUTPUT_FOLDER_NAME = "Sorted_By_Date"


def find_chat_file(folder: Path) -> Path | None:
    txt_files = list(folder.glob("*.txt"))
    if not txt_files:
        return None

    # Prefer chat-like txt if possible
    for f in txt_files:
        name = f.name.lower()
        if "chat" in name or "whatsapp" in name:
            return f

    return txt_files[0]


def parse_chat_file(chat_file: Path):
    """
    Returns list of tuples: (date_folder_name, filename)
    Example supported line:
    07/07/2025, 11:28 - Paps Th: VID-20250707-WA0009.mp4 (file attached)
    """
    entries = []

    pattern = re.compile(
        r"^(\d{2}/\d{2}/\d{4}),\s+\d{2}:\d{2}\s+-\s+.*?:\s+(.+?)\s+\(file attached\)?$",
        re.IGNORECASE
    )

    # Some exports may vary slightly, so we try a fallback too
    fallback_pattern = re.compile(
        r"^(\d{2}/\d{2}/\d{4}),\s+\d{2}:\d{2}\s+-\s+.*?:\s+(.+)$"
    )

    with chat_file.open("r", encoding="utf-8", errors="ignore") as f:
        for raw_line in f:
            line = raw_line.strip()

            match = pattern.match(line)
            if not match:
                fallback = fallback_pattern.match(line)
                if not fallback:
                    continue

                date_str, filename = fallback.groups()
                filename = filename.strip()

                # Keep only obvious file references from fallback
                if "." not in filename:
                    continue
            else:
                date_str, filename = match.groups()
                filename = filename.strip()

            try:
                date_obj = datetime.strptime(date_str, "%d/%m/%Y")
                date_folder = date_obj.strftime("%Y-%m-%d")
            except ValueError:
                continue

            ext = Path(filename).suffix.lower()
            if ext not in ALLOWED_EXTENSIONS:
                continue

            entries.append((date_folder, filename))

    return entries


def get_unique_destination(dest: Path) -> Path:
    if not dest.exists():
        return dest

    stem = dest.stem
    suffix = dest.suffix
    counter = 1

    while True:
        new_dest = dest.with_name(f"{stem}_{counter}{suffix}")
        if not new_dest.exists():
            return new_dest
        counter += 1


def main():
    if len(sys.argv) < 2:
        print("Drag and drop your exported WhatsApp folder onto this script.")
        input("Press Enter to exit...")
        return

    source_folder = Path(sys.argv[1])

    if not source_folder.exists() or not source_folder.is_dir():
        print("The dropped item is not a valid folder.")
        input("Press Enter to exit...")
        return

    chat_file = find_chat_file(source_folder)
    if not chat_file:
        print("No .txt chat file found in this folder.")
        input("Press Enter to exit...")
        return

    print(f"Chat file found: {chat_file.name}")

    entries = parse_chat_file(chat_file)
    if not entries:
        print("No attached files found in the chat file.")
        input("Press Enter to exit...")
        return

    output_root = source_folder / OUTPUT_FOLDER_NAME
    output_root.mkdir(exist_ok=True)

    copied = 0
    missing = 0
    processed = set()

    for date_folder, filename in entries:
        # Avoid exact duplicate processing
        key = (date_folder, filename)
        if key in processed:
            continue
        processed.add(key)

        src = source_folder / filename
        if not src.exists():
            print(f"Missing file: {filename}")
            missing += 1
            continue

        dest_folder = output_root / date_folder
        dest_folder.mkdir(parents=True, exist_ok=True)

        dest = dest_folder / filename
        dest = get_unique_destination(dest)

        shutil.copy2(src, dest)
        print(f"Copied: {filename} -> {date_folder}")
        copied += 1

    print("\nDone.")
    print(f"Copied files: {copied}")
    print(f"Missing referenced files: {missing}")
    print(f"Output folder: {output_root}")

    input("\nPress Enter to exit...")


if __name__ == "__main__":
    main()