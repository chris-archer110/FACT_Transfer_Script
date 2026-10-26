from utils import *
from consts import *

def setup():
    """
    Prompt the user for input and set up the configuration dictionary.
    """
    config = {}
    while True:
        config['rip_mode'] = ask(
            "CD read mode (fast disables error verification/correction; quality keeps it enabled)",
            "fast",
        ).lower()
        if config['rip_mode'] in {"fast", "quality"}:
            break
        print("Please enter 'fast' or 'quality'.")

    config['cd_device'] = ask("Enter the CD drive device path (leave blank to auto-detect): ")
    config['track_numbers'] = get_cd_track_numbers(config['cd_device'])
    config['num_tracks'] = len(config['track_numbers'])
    print(f"Identified {config['num_tracks']} tracks.")
    config['staging_dir'] = FACT_STAGING_DIR
    config['backed_up_dir'] = FACT_BACKUP_DIR
    config['prev_fact_number'] = get_previous_FACT_number()
    config['cd_call_number'] = ask("Enter the CD Call number (CDxxxx): ")
    config['orig_call_number'] = ask("Enter the original Call number (XXyyyy): ")

    return config

def run():
    config = setup()
    fact_entry = generate_new_fact_entry(config)
    print(f"GENERATED FACT ENTRY: {fact_entry}")
    staged_files = stage_cd_tracks(config)
    print(f"STAGING COMPLETE. Please verify the files in {config['staging_dir'] + '/' + fact_entry} are correct and label any dead tracks with '_DEAD' as a suffix.")

run()