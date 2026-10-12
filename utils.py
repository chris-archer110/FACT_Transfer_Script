"""
Generating the FACT entry:

Place CD in drive and close

Find CD File Location

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


def run(cmd: list[str], capture: bool = True, check: bool = False) -> str:
    """Run a shell command; returns stdout (or '' when capture=False)."""
    result = subprocess.run(cmd, capture_output=capture, text=True)
    if check and result.returncode != 0:
        raise RuntimeError(
            f"Command failed ({' '.join(cmd)}):\n{result.stderr or result.stdout}"
        )
    return (result.stdout or "") if capture else ""

def count_cd_tracks(folder_path: str) -> int:
    """Open a CD folder, identify the number of tracks, and print it."""
    folder = Path(folder_path)

    if not folder.exists():
        raise FileNotFoundError(f"CD Folder Not Found")
    if not folder.is_dir():
        raise NotADirectoryError(f"Not a CD Folder: {folder}")

    track_count = sum(
        1 for file in folder.iterdir()
        if file.is_file() and file.suffix.lower() in AUDIO_EXTENSIONS
    )

    print(f"Identified {track_count} tracks.")
    return track_count

def get_previous_FACT_number():
    """
    Retrieve the last used FACT number from the staging directory. If the staging directory is empty, check the backup directory.
    """
    
    folder  = Path(STAGING_DIR)
    FACT_numbers = [int(file.stem.split('_')[1]) for file in folder.iterdir() if file.is_file() and file.stem.startswith('FACT_')]
    
    if FACT_numbers:
        prev_FACT = max(FACT_numbers)
    else:
        backup_folder = Path(BACKUP_DIR)
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
    """Copy every audio track from the CD folder into the new staging folder, 
        renaming them to the FACT nomenclature and adding a track numbers

    Track numbers are taken from the original filename when present;

    Returns the list of staged files.
    """
    cd_folder = Path(config['cd_folder'])

    if not cd_folder.exists():
        raise FileNotFoundError(f"CD folder not found: {cd_folder}")
    if not cd_folder.is_dir():
        raise NotADirectoryError(f"Not a folder: {cd_folder}")

    fact_entry = generate_new_fact_entry(config)
    FACT_dir = Path(config['staging_directory']) / fact_entry
    FACT_dir.mkdir(parents=True)

    for i,file in enumerate(cd_folder.iterdir()):
        if file.is_file() and file.suffix.lower() in AUDIO_EXTENSIONS:
            print(f"Found audio file: {file.name}")
        destination = FACT_dir/ f"{fact_entry}_{str(i+1).zfill(2)}{file.suffix.lower()}"

        shutil.copy2(file, destination)
        staged_files.append(destination)
        print(f"Copied {file.name} -> {destination}")

    print(f"Copied all {len(staged_files)} track(s) into {FACT_dir}")
    return staged_files

