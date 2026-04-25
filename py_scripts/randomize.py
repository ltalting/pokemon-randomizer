from datetime import datetime
from json import dumps
from os import environ
from pathlib import Path
from sys import path as SysPath, stderr, exit
from typing import Union

# Upstream imports
FILE_PATH = Path(__file__)
# Get absolute path of this file
abs_path = FILE_PATH.resolve()
current_dir = abs_path.parent
# "Walk" the file's absolute path towards the filesystem's root until the root_dir_name is found
root_dir_names = ["pokemon-randomizer"]
while current_dir.name not in root_dir_names:
    # If the current_dir's parent is itself, we are at system root and were unable find the root_dir_name
    if current_dir.parent == current_dir:
        stderr.write(dumps({
            "status": "errored",
            "message": f"Did not find project root '{root_dir_names}' during imports in {FILE_PATH}"
        }))
        exit(1)
    current_dir = current_dir.parent
# Overwrite sys.path with root dir
if current_dir not in SysPath:
    SysPath.insert(0, str(current_dir))
from custom_shared.control_functions import log_msg, run_cmd
from custom_shared.filesystem_functions import get_path, extensions, FileLike, DirectoryMetadata
from custom_shared.question_master import ask_question
from custom_shared.parsers import parse_env_file

# Use SysPath detected project root
ROOT = SysPath[0]
parse_env_file(Path(ROOT + "/.env"))

# Load env vars
try:
    originals = get_path(ROOT + environ.get("ORIGINALS_DIR"))
    settings = get_path(ROOT + environ.get("SETTINGS_DIR"))
    randomizer = get_path(ROOT + environ.get("RANDOMIZER_JAR"))
except Exception as e:
    log_msg("ERROR: " + str(e), "red", exit = 1)

# Function to call sub process for randomization
def randomize_rom(rom_file_meta: Union[FileLike, DirectoryMetadata]):
    log_msg(f"ROM loaded from {str(rom_file_meta.path)}...", "blue")
    should_randomize = ask_question(f"Would you like to create a randomized version of '{rom_file_meta.name}'?", ["y", "n"], "blue")
    if should_randomize == "y":
        settings_options: set[str] = []
        # Loop through files in settings directory, appending files with universalpokemon settings file extensions
        # to the settings_options list
        for file in settings.files:
            settings_file_meta = get_path(file)
            if settings_file_meta.extension in extensions.APP_EXTENSIONS["universalpokemonrandomizer"]:
                settings_options.append(settings_file_meta.ext_name)
        
        # Create a list of valid options, which are numbers from a selection list
        # This is just for printing options along with the question
        valid_answers: list[str] = [str(x) for x in list(range(1, len(settings_options) + 1))]
        # Print each option (setting name) with its associated index
        for option, setting_name in enumerate(settings_options, 1):
            log_msg(f"{option}) {setting_name}", "blue", 1)
        selected_setting_index = int(ask_question("Which setting would you like to randomize with? ", valid_answers)) - 1
        settings_path = settings.path / settings_options[selected_setting_index]
        rom_file_name = ask_question("What would you like to name the file?", color = "blue")
        if rom_file_name == "":
            rom_file_name = (rom_file_meta.name + datetime.now().isoformat(timespec='milliseconds')).replace(" ", "").replace(":", ".")
        output_location = Path(ROOT) / "randomized" / rom_file_name
        print(output_location)
        command = [
            "java",
            "-jar",
            str(randomizer.path),
            "cli",
            "-i",
            str(rom_file_meta.path),
            "-o",
            output_location,
            "-s",
            str(settings_path), 
            "-l"
        ]
        run_cmd(command, working_dir = randomizer.path.parent)
    else:
        log_msg(f"Skipping {str(rom_file_meta.path)}", "yellow")

# Start of script
log_msg(f"Scanning {originals.path} ...", "blue")

total_files = len(originals.files)
originals_files_printable = "\n".join(
    f"  {index}) {file.name}"
    for index, file in enumerate(originals.files, 1)
)

log_msg(originals_files_printable, "green")

# Ensure randomized folder
Path("./randomized").mkdir(parents = True, exist_ok = True)

# main
valid_answers = (range(1, total_files), True)
one_or_all = ask_question("Submit a number to randomize a specific file or press Enter to step through list:", valid_answers, "blue")
if len(one_or_all) <= 0:
    log_msg("No selection provided. Stepping through list...", "yellow")
    for index, file in enumerate(originals.files):
        if index != 0:
            log_msg("")
        rom_file_meta = get_path(file)
        # Follow and load in a .lnk shortcut file's target rather than the link itself
        if rom_file_meta.extension in extensions.LINK_EXTENSIONS:
            log_msg(f"Resolving {str(rom_file_meta.path)} target...", "blue")
            rom_file_meta = get_path(rom_file_meta.target_path)
            log_msg("Target: " + str(rom_file_meta.path), "green", 1)
        if rom_file_meta.extension not in extensions.ROM_EXTENSIONS:
            log_msg(f"ERROR: File is not a ROM file.", "red")
            continue
        randomize_rom(rom_file_meta)
else:
    rom_file_meta = get_path(originals.files[int(one_or_all) - 1])
    # Follow and load in a .lnk shortcut file's target rather than the link itself
    if rom_file_meta.extension in extensions.LINK_EXTENSIONS:
        log_msg(f"Resolving {str(rom_file_meta.path)} target...", "blue")
        rom_file_meta = get_path(rom_file_meta.target_path)
        log_msg("Target: " + str(rom_file_meta.path), "green", 1)
    if rom_file_meta.extension not in extensions.ROM_EXTENSIONS:
        log_msg(f"ERROR: File is not a ROM file.", "red")
    randomize_rom(rom_file_meta)
