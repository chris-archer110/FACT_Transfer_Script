"""Synchronize a reviewed FACT staging folder with the database and Google Sheets."""

import argparse
import json
import os
import re
import shutil
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlsplit
from urllib.request import Request, urlopen
from typing import Optional, Union

from consts import (
    AUDIO_EXTENSIONS,
    DATABASE_API_AUTH_HEADER,
    DATABASE_API_AUTH_PREFIX,
    DATABASE_API_TOKEN_ENV,
    DATABASE_LOOKUP_URL_TEMPLATE,
    DATABASE_RECORD_CALL_NUMBER_FIELD,
    DATABASE_NOTES_FIELD,
    DATABASE_RECORD_ID_FIELD,
    DATABASE_RECORDS_KEY,
    DATABASE_UPDATE_URL_TEMPLATE,
    FACT_BACKUP_DIR,
    FACT_STAGING_DIR,
    GOOGLE_SERVICE_ACCOUNT_FILE,
    GOOGLE_SPREADSHEET_TITLE,
)


from utils import *


def synchronize(folder: Path, confirm: bool = True) -> Path:
    staging_dir = Path(FACT_STAGING_DIR).expanduser().resolve(strict=True)
    folder = folder.expanduser().resolve(strict=True)
    if folder.parent != staging_dir or not folder.is_dir():
        raise ValueError(f"Choose a FACT folder directly inside {staging_dir}.")

    fact_number, cd_call_number = parse_fact_folder(folder)
    fact_entry = folder.name
    backup_dir = Path(FACT_BACKUP_DIR).expanduser().resolve()
    backup_folder = backup_dir / folder.name
    if backup_folder.exists():
        raise FileExistsError(f"Backup destination already exists: {backup_folder}")

    print(f"FACT folder: {folder}")
    print(f"Database record: {cd_call_number} (append {fact_entry} to notes)")
    print(
        f"Google Sheet: {GOOGLE_SPREADSHEET_TITLE}; "
        f"match Call_Number={cd_call_number}, check completion, set FACT={fact_number}"
    )
    print(f"After successful updates, move folder to: {backup_folder}")
    if confirm and input("Proceed with synchronization? [y/N]: ").strip().lower() != "y":
        print("Synchronization cancelled; no changes made.")
        return folder

    #update_database(cd_call_number, fact_entry)
    update_google_sheet(cd_call_number, fact_number)
    backup_dir.mkdir(parents=True, exist_ok=True)
    shutil.move(str(folder), str(backup_folder))
    print(f"Synchronization complete; archived folder at {backup_folder}")
    return backup_folder


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Update the database and CD_Transfer_Progress for a FACT folder."
    )
    parser.add_argument(
        "folder",
        nargs="?",
        help="FACT folder in the staging directory (prompts if omitted)",
    )
    args = parser.parse_args()
    try:
        folder = resolve_staging_folder(args.folder)
        synchronize(folder)
    except (OSError, RuntimeError, ValueError, KeyError) as exc:
        print(f"Synchronization failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
