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
            _run_cdparanoia(
                ["-w", str(track_number), str(partial_output)],
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