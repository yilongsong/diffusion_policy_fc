import sys
import pathlib
import subprocess
import click

@click.command()
@click.option('-i', '--input_dir', required=True, help='Input directory containing hdf5 files')
@click.option('-o', '--output_dir', required=True, help='Output directory for processed hdf5 files')
@click.option('-n', '--num_workers', default=None, type=int, help='Number of workers for multiprocessing')
@click.option('-e', '--eval_dir', default=None, help='Directory for output evaluation metrics (optional)')
def batch_process(input_dir, output_dir, num_workers, eval_dir):
    # Convert input and output directories to pathlib Paths
    input_dir = pathlib.Path(input_dir).expanduser()
    output_dir = pathlib.Path(output_dir).expanduser()

    # Ensure the input directory exists
    if not input_dir.is_dir():
        print(f"Input directory {input_dir} does not exist.")
        return

    # Create the output directory if it doesn't exist
    output_dir.mkdir(parents=True, exist_ok=True)

    # Get all hdf5 files in the input directory
    hdf5_files = list(input_dir.glob("*.hdf5"))
    
    if not hdf5_files:
        print(f"No hdf5 files found in {input_dir}.")
        return

    # Iterate over each HDF5 file
    for input_file in hdf5_files:
        output_file = output_dir / f"{input_file.stem}_abs.hdf5"
        print(f"Processing {input_file} and saving to {output_file}")
        # Build the command to run robomimic_dataset_conversion.py
        command = [
            "python", "/home/yilong/Documents/diffusion_policy/diffusion_policy/scripts/robomimic_dataset_conversion.py",
            "--input", str(input_file),
            "--output", str(output_file)
        ]
        
        # Optionally add the evaluation directory
        if eval_dir:
            eval_path = pathlib.Path(eval_dir).expanduser() / f"{input_file.stem}_eval"
            command.extend(["--eval_dir", str(eval_path)])

        # Add the number of workers if provided
        if num_workers:
            command.extend(["--num_workers", str(num_workers)])

        # Run the command for the current HDF5 file
        subprocess.run(command)

if __name__ == "__main__":
    batch_process()