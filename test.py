import h5py
import numpy as np

def explore_hdf5(hdf5_path):
    """
    Print out the structure of an HDF5 file recursively:
    groups, datasets, shapes, and attributes.
    """

    def print_attrs(name, obj):
        print(f"--- Name: {name} ---")
        if isinstance(obj, h5py.Dataset):
            print(f"  Type: Dataset")
            print(f"  Shape: {obj.shape}")
            print(f"  Dtype: {obj.dtype}")
        elif isinstance(obj, h5py.Group):
            print(f"  Type: Group")
        # Print attributes
        for key, val in obj.attrs.items():
            print(f"  Attr [{key}]: {val}")
        print("")

    with h5py.File(hdf5_path, "r") as f:
        f.visititems(print_attrs)

# Usage
hdf5_file = "data/robomimic/datasets/lift/obs/lift_300_obs_megapose.hdf5"
explore_hdf5(hdf5_file)