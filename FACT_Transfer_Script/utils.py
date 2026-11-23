"""
Generating the FACT entry:

Place CD in drive and close

Select the CD drive; tracks are ripped directly into the staging folder

Rename each file following this naming convention:
a. FACT (Freedom Archives Cloud Technology)
b. The 4-digit internal reference (identification) number. This 4-digit number
should correspond to the previously created FACT folder number
c. Only if the CD has multiple tracks on it, add a 2-digit track number to the
end of the file name (ex “FACT_0006_01”; “FACT_0006_02”;
“FACT_0006_03”; etc)
d. “_DEAD” at the end of a file name means that this file is not archival
material (ex “FACT_0006_27_DEAD”), i.e. tracks that are blank or false
starts or otherwise not useful [TO BE DONE MANUALLY]

[MANUAL] Preview each track by selecting it and pressing the space bar, to make sure each
track is working (if you hear nothing on any tracks, you may need to raise the
volume on the mixer channel “11/12” and/or power on the monitor speakers to
get audio from this computer)
** For any tracks that are blank or false starts or otherwise not useful
tracks, add the suffix “_DEAD” after the track name

Updating the database

Go to the internal search function for the Freedom Archives website
a. search.freeedomarchives.org/admin

Search for the associated CD (ex “CD 415”)

In the notes section paste the entire nomenclature for the folder title from
“Naming Your Folder” (ex: FACT_0006_KP624_CD1072)

Updating the Spreadsheet

Pull up the spreadsheet “CD_Transfer_Progress” and check off the box
associated with the CD record you just transferred to indicate it’s complete
"""

from consts import *

from pathlib import Path
import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
import wave
from typing import Optional


def ask(prompt: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    answer = input(f"{prompt}{suffix}: ").strip()
    return answer or default


def ask_int(prompt: str, lo: int, hi: int, default: int ) -> int:
    while True:
        raw = ask(prompt, str(default) if default is not None else "")
        try:
            val = int(raw)
        except ValueError:
            print("   Please enter a whole number.")
            continue
        if lo <= val <= hi:
            return val
        print(f"   Please enter a number between {lo} and {hi}.")

def _run_cdparanoia(arguments: list[str], cd_device: str = "") -> str:
    executable = shutil.which("cd-paranoia") or shutil.which("cdparanoia")
    if executable is None:
        raise FileNotFoundError(
            "The 'cd-paranoia' utility is required to rip audio CDs. "
            "Install it with Homebrew using 'brew install libcdio-paranoia' "
            "and ensure it is available on PATH."
        )

    command = [executable]
    if cd_device:
        command.extend(["-d", cd_device])
    command.extend(arguments)

    result = subprocess.run(command, capture_output=True, text=True)
    output = "\n".join(part for part in (result.stdout, result.stderr) if part)
    if result.returncode != 0:
        raise RuntimeError(
            f"cdparanoia failed with exit code {result.returncode}:\n"
            f"{output or 'No output from cdparanoia.'}"
        )
    return output


def get_cd_track_numbers(cd_device: str = "") -> list[int]:
    """Return audio track numbers from the CD in the selected drive."""
    output = _run_cdparanoia(["-Q"], cd_device)
    track_numbers = [
        int(match.group(1))
        for match in re.finditer(r"(?m)^\s*(\d+)\.\s+\d+\s+\[", output)
    ]
    if not track_numbers and not re.search(r"Table of contents", output, re.IGNORECASE):
        raise RuntimeError(f"Could not read the audio CD table of contents:\n{output}")
    return track_numbers


def count_cd_tracks(cd_device: str = "") -> int:
    """Identify the number of audio tracks on the CD in the selected drive."""
    track_count = len(get_cd_track_numbers(cd_device))
    print(f"Identified {track_count} tracks.")
    return track_count


def _validate_ripped_wav(path: Path) -> None:
    try:
        with wave.open(str(path), "rb") as audio:
            if (
                audio.getnchannels() != 2
                or audio.getsampwidth() != 2
                or audio.getframerate() != 44100
                or audio.getnframes() == 0
            ):
                raise ValueError(f"Ripped track is not valid CD-quality audio: {path}")
    except (OSError, wave.Error) as exc:
        raise ValueError(f"Ripped track is not a valid WAV file: {path}") from exc


def get_previous_FACT_number():
    """
    Retrieve the last used FACT number from the staging directory. If the staging directory is empty, check the backup directory.
    """
    
    folder  = Path(FACT_STAGING_DIR)
    FACT_numbers = [int(file.stem.split('_')[1]) for file in folder.iterdir() if file.stem.startswith('FACT_')]
    
    if FACT_numbers:
        prev_FACT = max(FACT_numbers)
    else:
        backup_folder = Path(FACT_BACKUP_DIR)
        FACT_numbers = [int(file.stem.split('_')[1]) for file in backup_folder.iterdir() if file.is_file() and file.stem.startswith('FACT_')]
        if FACT_numbers:
            prev_FACT = max(FACT_numbers)
        else:
            raise ValueError("No previous FACT numbers found in staging or backup directories.")
    
    print(f"Last used FACT number: {prev_FACT}")
    return prev_FACT

def generate_new_fact_entry(config):
    # Generate the FACT entry
    fact_entry = f"FACT_{str(config['prev_fact_number'] + 1).zfill(4)}_{config['orig_call_number']}_{config['cd_call_number']}"
    print(f"Generated FACT entry: {fact_entry}")
    
    return fact_entry


def stage_cd_tracks(config, overwrite: bool = False) -> list[Path]:
    """Rip audio tracks from the CD directly into a new FACT staging folder."""
    cd_device = config.get("cd_device", "")
    rip_mode = config.get("rip_mode", "quality")
    if rip_mode not in {"fast", "quality"}:
        raise ValueError("Rip mode must be 'fast' or 'quality'.")

    track_numbers = config.get("track_numbers")
    if track_numbers is None:
        track_numbers = get_cd_track_numbers(cd_device)
    if not track_numbers:
        raise ValueError("No audio tracks found on the CD.")

    fact_entry = generate_new_fact_entry(config)
    FACT_dir = Path(config['staging_dir']) / fact_entry
    FACT_dir.mkdir(parents=True)

    staged_files = []
    try:
        for position, track_number in enumerate(track_numbers, start=1):
            track_suffix = f"_{position:02d}" if len(track_numbers) > 1 else ""
            destination = FACT_dir / f"{fact_entry}{track_suffix}.wav"
            partial_output = FACT_dir / f".{destination.name}.partial"

            print(f"Ripping CD track {track_number} -> {destination}")
            rip_options = ["-Z"] if rip_mode == "fast" else []
            _run_cdparanoia(
                [*rip_options, "-w", str(track_number), str(partial_output)],
                cd_device,
            )
            _validate_ripped_wav(partial_output)
            partial_output.replace(destination)
            staged_files.append(destination)
    except (OSError, RuntimeError, ValueError) as exc:
        try:
            shutil.rmtree(FACT_dir)
        except OSError as cleanup_error:
            raise RuntimeError(
                f"CD ripping failed ({exc}); partial output remains in "
                f"{FACT_dir} because cleanup also failed: {cleanup_error}"
            ) from cleanup_error
        raise

    print(f"Ripped {len(staged_files)} track(s) into {FACT_dir}")
    return staged_files

#UTILS FOR SYNCHRONIZE_DATA.PY

def parse_fact_folder(folder: Path) -> tuple[str, str]:
    match = re.fullmatch(r"FACT_(\d+)_.+_(CD\d+)", folder.name, re.IGNORECASE)
    if match is None:
        raise ValueError(
            f"Folder name must match FACT_<number>_<original call #>_<CD call #>: {folder.name}"
        )
    return match.group(1), match.group(2)


def resolve_staging_folder(folder_arg: Optional[str]) -> Path:
    staging_dir = Path(FACT_STAGING_DIR).expanduser().resolve(strict=True)
    if folder_arg:
        folder = Path(folder_arg).expanduser().resolve(strict=True)
    else:
        candidates = sorted(
            path for path in staging_dir.iterdir()
            if path.is_dir() and re.fullmatch(
                r"FACT_\d+_.+_(CD\d+)", path.name, re.IGNORECASE
            )
        )
        if not candidates:
            raise FileNotFoundError(f"No FACT folders found in {staging_dir}")
        if len(candidates) == 1:
            folder = candidates[0]
        else:
            print("FACT folders available to synchronize:")
            for index, candidate in enumerate(candidates, start=1):
                print(f"  {index}. {candidate.name}")
            selection = input("Select a folder number: ").strip()
            try:
                folder = candidates[int(selection) - 1]
            except (ValueError, IndexError) as exc:
                raise ValueError("Select a valid folder number.") from exc

    if folder.parent != staging_dir or not folder.is_dir():
        raise ValueError(f"Choose a FACT folder directly inside {staging_dir}.")
    if not any(
        file.is_file() and file.suffix.lower() in AUDIO_EXTENSIONS
        for file in folder.iterdir()
    ):
        raise ValueError(f"No audio tracks found in FACT folder: {folder}")
    return folder


def _google_services():
    if not GOOGLE_SERVICE_ACCOUNT_FILE:
        raise RuntimeError(
            "Set GOOGLE_SERVICE_ACCOUNT_FILE in consts.py to the local "
            "service-account credential file path."
        )
    credential_path = Path(GOOGLE_SERVICE_ACCOUNT_FILE).expanduser()
    if not credential_path.is_file():
        raise FileNotFoundError(
            f"Google service-account credential file not found: {credential_path}"
        )

    try:
        from google.oauth2.service_account import Credentials
        from googleapiclient.discovery import build
    except ImportError as exc:
        raise RuntimeError(
            "Install Google API dependencies with "
            "'python3 -m pip install -r requirements.txt'."
        ) from exc

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive.readonly",
    ]
    credentials = Credentials.from_service_account_file(
        str(credential_path), scopes=scopes
    )
    return (
        build("drive", "v3", credentials=credentials, cache_discovery=False),
        build("sheets", "v4", credentials=credentials, cache_discovery=False),
    )


def _execute_google_request(request):
    from googleapiclient.errors import HttpError

    try:
        return request.execute()
    except HttpError as exc:
        raise RuntimeError(f"Google API request failed: {exc}") from exc


def _find_spreadsheet_id(drive_service, spreadsheet_link: str) -> str:
    match = re.fullmatch(
        r"https://docs\.google\.com/spreadsheets/d/([A-Za-z0-9_-]+)(?:[/?#].*)?",
        spreadsheet_link.strip(),
    )
    if match is None:
        raise RuntimeError(
            "Provide a valid Google Sheets link (https://docs.google.com/"
            "spreadsheets/d/<spreadsheet-id>); spreadsheet IDs, titles, and "
            "file paths are not accepted."
        )
    return match.group(1)


def _find_progress_sheet(sheets_service, spreadsheet_id: str):
    """Find the unique sheet tab with Call_Number and FACT headers."""
    metadata = sheets_service.spreadsheets().get(
        spreadsheetId=spreadsheet_id,
        fields="sheets(properties(sheetId,title))",
    )
    metadata = _execute_google_request(metadata)

    matching_tabs = []
    for sheet in metadata.get("sheets", []):
        properties = sheet["properties"]
        title = properties["title"]
        quoted_title = "'" + title.replace("'", "''") + "'"
        header_response = sheets_service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=f"{quoted_title}!A1:ZZ1",
        )
        header_response = _execute_google_request(header_response)
        headers = header_response.get("values", [[]])[0]
        first_header = headers[0] if headers else ""
        if (
            not first_header
            and "Call_Number" in headers
            and "FACT" in headers
        ):
            matching_tabs.append((properties, headers))

    if len(matching_tabs) != 1:
        raise RuntimeError(
            "Expected exactly one sheet tab with Call_Number and FACT headers; "
            f"found {len(matching_tabs)}."
        )

    properties, headers = matching_tabs[0]
    quoted_title = "'" + properties["title"].replace("'", "''") + "'"
    return properties, headers, quoted_title


def _find_matching_row_number(
    sheets_service,
    spreadsheet_id: str,
    quoted_title: str,
    headers: list[str],
    cd_call_number: str,
) -> int:
    """Return the unique row matching the requested Call_Number."""
    call_column = headers.index("Call_Number")
    values_response = sheets_service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id,
        range=f"{quoted_title}!A2:ZZ2000",
    )
    values_response = _execute_google_request(values_response)
    rows = values_response.get("values", [])

    def normalize_call(value: object) -> str:
        return "".join(str(value).upper().split())

    matches = [
        (row_index, row)
        for row_index, row in enumerate(rows, start=2)
        if len(row) > call_column
        and normalize_call(row[call_column]) == normalize_call(cd_call_number)
    ]
    if len(matches) != 1:
        raise RuntimeError(
            f"Expected one spreadsheet row for {cd_call_number}; found {len(matches)}."
        )
    return matches[0][0]


def _read_spreadsheet_row(
    sheets_service,
    spreadsheet_id: str,
    quoted_title: str,
    row_number: int,
    cd_call_number: str,
) -> list[dict]:
    """Read the selected row's entered values for a preserving update."""
    row_response = sheets_service.spreadsheets().get(
        spreadsheetId=spreadsheet_id,
        ranges=[f"{quoted_title}!A{row_number}:ZZ{row_number}"],
        includeGridData=True,
        fields="sheets(data(rowData(values(userEnteredValue))))",
    )
    row_response = _execute_google_request(row_response)
    sheet_data = row_response.get("sheets", [])
    grid_data = sheet_data[0].get("data", []) if sheet_data else []
    row_data = grid_data[0].get("rowData", []) if grid_data else []
    if not row_data:
        raise RuntimeError(
            f"Could not read spreadsheet row {row_number} for {cd_call_number}."
        )

    return [
        {"userEnteredValue": dict(cell["userEnteredValue"])}
        if "userEnteredValue" in cell
        else {}
        for cell in row_data[0].get("values", [])
    ]


def _build_row_update(
    row_values: list[dict],
    headers: list[str],
    sheet_id: int,
    row_number: int,
    fact_entry: str,
) -> dict:
    """Build a full-row update preserving values except FACT and completion."""
    fact_column = headers.index("FACT")
    row_width = max(len(headers), len(row_values), fact_column + 1, 1)
    row_values.extend({} for _ in range(row_width - len(row_values)))
    row_values[0] = {"userEnteredValue": {"boolValue": True}}
    row_values[fact_column] = {
        "userEnteredValue": {"stringValue": fact_entry}
    }

    return {
        "updateCells": {
            "range": {
                "sheetId": sheet_id,
                "startRowIndex": row_number - 1,
                "endRowIndex": row_number,
                "startColumnIndex": 0,
                "endColumnIndex": row_width,
            },
            "rows": [{"values": row_values}],
            "fields": "userEnteredValue",
        }
    }


def _write_spreadsheet_row(
    sheets_service,
    spreadsheet_id: str,
    row_update: dict,
) -> None:
    """Submit the row replacement to Google Sheets."""
    request = sheets_service.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id,
        body={"requests": [row_update]},
    )
    _execute_google_request(request)


def update_google_sheet(
    cd_call_number: str,
    fact_entry: str,
    spreadsheet_link: str = "",
) -> None:
    """Update FACT and completion on the unique matching spreadsheet row."""
    drive_service, sheets_service = _google_services()
    spreadsheet_id = _find_spreadsheet_id(drive_service, spreadsheet_link)
    properties, headers, quoted_title = _find_progress_sheet(
        sheets_service, spreadsheet_id
    )
    row_number = _find_matching_row_number(
        sheets_service, spreadsheet_id, quoted_title, headers, cd_call_number
    )
    row_values = _read_spreadsheet_row(
        sheets_service,
        spreadsheet_id,
        quoted_title,
        row_number,
        cd_call_number,
    )
    row_update = _build_row_update(
        row_values, headers, properties["sheetId"], row_number, fact_entry
    )
    _write_spreadsheet_row(sheets_service, spreadsheet_id, row_update)
    print(
        f"Checked the completion box and set FACT={fact_entry} "
        f"for {cd_call_number}."
    )