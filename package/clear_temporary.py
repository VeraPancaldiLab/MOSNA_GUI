from pathlib import Path
import shutil
import argparse

def clear_temp_folder(working_dir: str) -> int:
    """
    This function removes the temp folder located in the selected working directory.
    It does nothing if the folder does not exist.
    """
    temp_dir = Path(working_dir) / "temp"

    if temp_dir.exists() and temp_dir.is_dir():
        shutil.rmtree(temp_dir)
        print(f"Temporary folder removed: {temp_dir}")
    else:
        print(f"No temporary folder found at: {temp_dir}")

    return 0

def main() -> int:
    parser = argparse.ArgumentParser(description="Remove the temp folder from a working directory.")
    parser.add_argument("--working_dir", required=True, help="Path to the working directory")
    args = parser.parse_args()

    return clear_temp_folder(args.working_dir)

if __name__ == "__main__":
    raise SystemExit(main())