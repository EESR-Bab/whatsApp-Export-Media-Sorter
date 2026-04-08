import sys
import re
import shutil
import zipfile
import tempfile
from pathlib import Path
from datetime import datetime

ALLOWED_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".gif", ".webp", ".heic",
    ".mp4", ".mov", ".avi", ".mkv", ".3gp",
    ".mp3", ".m4a", ".aac", ".opus",
    ".pdf", ".doc", ".docx"
}

SORTED_MEDIA_FOLDER_NAME = "Sorted Media"


def find_chat_file(folder: Path) -> Path | None:
    txt_files = list(folder.glob("*.txt"))
    if not txt_files:
        return None

    for f in txt_files:
        name = f.name.lower()
        if "chat" in name or "whatsapp" in name:
            return f

    return txt_files[0]


def parse_chat_file(chat_file: Path):
    entries = []

    pattern = re.compile(
        r"^(\d{2}/\d{2}/\d{4}),\s+\d{2}:\d{2}\s+-\s+.*?:\s+(.+?)\s+\(file attached\)$",
        re.IGNORECASE
    )

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


def copy_chat_txt(chat_file: Path, output_root: Path) -> Path:
    dest = output_root / chat_file.name
    dest = get_unique_destination(dest)
    shutil.copy2(chat_file, dest)
    return dest


def process_export_folder(source_folder: Path, output_base_parent: Path, output_name: str):
    print(f"Processing folder: {source_folder}")

    chat_file = find_chat_file(source_folder)
    if not chat_file:
        print("No .txt chat file found in this folder.")
        return False

    print(f"Chat file found: {chat_file.name}")

    entries = parse_chat_file(chat_file)
    if not entries:
        print("No attached files found in the chat file.")
        return False

    output_root = output_base_parent / output_name
    output_root.mkdir(parents=True, exist_ok=True)

    sorted_media_root = output_root / SORTED_MEDIA_FOLDER_NAME
    sorted_media_root.mkdir(exist_ok=True)

    copied_chat = copy_chat_txt(chat_file, output_root)
    print(f"Copied chat file to: {copied_chat}")

    copied = 0
    missing = 0
    processed = set()

    for date_folder, filename in entries:
        key = (date_folder, filename)
        if key in processed:
            continue
        processed.add(key)

        src = source_folder / filename
        if not src.exists():
            print(f"Missing file: {filename}")
            missing += 1
            continue

        dest_folder = sorted_media_root / date_folder
        dest_folder.mkdir(parents=True, exist_ok=True)

        dest = dest_folder / filename
        dest = get_unique_destination(dest)

        shutil.copy2(src, dest)
        print(f"Copied: {filename} -> {SORTED_MEDIA_FOLDER_NAME}\\{date_folder}")
        copied += 1

    print("\nDone.")
    print(f"Copied media files: {copied}")
    print(f"Missing referenced files: {missing}")
    print(f"Output folder: {output_root}")
    return True


def main():
    if len(sys.argv) < 2:
        print("Drag and drop a WhatsApp export folder or .zip onto this tool.")
        input("Press Enter to exit...")
        return

    input_path = Path(sys.argv[1]).resolve()
    print(f"Input received: {input_path}")

    if not input_path.exists():
        print("The input path does not exist.")
        input("Press Enter to exit...")
        return

    try:
        if input_path.is_dir():
            output_name = f"{input_path.name}_sorted"
            success = process_export_folder(
                source_folder=input_path,
                output_base_parent=input_path.parent,
                output_name=output_name
            )

        elif input_path.is_file() and input_path.suffix.lower() == ".zip":
            output_name = f"{input_path.stem}_sorted"

            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                extract_folder = temp_path / "extracted"
                extract_folder.mkdir(parents=True, exist_ok=True)

                print(f"Extracting zip to temporary folder: {extract_folder}")

                with zipfile.ZipFile(input_path, "r") as zip_ref:
                    zip_ref.extractall(extract_folder)

                # Try root first
                working_folder = extract_folder
                chat_file = find_chat_file(working_folder)

                # If txt not found at root and there's only one subfolder, try inside it
                if not chat_file:
                    subdirs = [p for p in extract_folder.iterdir() if p.is_dir()]
                    if len(subdirs) == 1:
                        working_folder = subdirs[0]
                        chat_file = find_chat_file(working_folder)

                if not chat_file:
                    print("No .txt chat file found inside the zip.")
                    input("Press Enter to exit...")
                    return

                success = process_export_folder(
                    source_folder=working_folder,
                    output_base_parent=input_path.parent,
                    output_name=output_name
                )

        else:
            print("Unsupported input. Please drop a folder or a .zip file.")
            input("Press Enter to exit...")
            return

        if not success:
            print("Processing failed.")
        input("\nPress Enter to exit...")

    except zipfile.BadZipFile:
        print("The file is not a valid zip archive.")
        input("Press Enter to exit...")
    except Exception as e:
        print(f"Unexpected error: {e}")
        input("Press Enter to exit...")


if __name__ == "__main__":
    main()