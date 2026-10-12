from utils import *
from consts import *

def setup():
    """
    Prompt the user for input and set up the configuration dictionary.
    """
    config = {}
    config['input_dir'] = ask("Enter the path to the CD file location (or drag and drop the CD File): ")
    config['num_tracks'] =count_cd_tracks(config['input_dir'])
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
    print(f"ADDED THE FOLLOWING FILES TO{config['staging_dir'] + '/' + fact_entry}: {staged_files}")
    print(f"STAGING COMPLETE. Please verify the files in {config['staging_dir'] + '/' + fact_entry} are correct and label any dead tracks with '_DEAD' as a suffix.")

run()