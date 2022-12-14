import numpy as np

from platform import system
import os
import pickle

from pathlib import Path
from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, Union, List, Any, Tuple

# from aicsimageio.writers import OmeTiffWriter
# from napari_aicsimageio.core import reader_function
from ._aicsimage_reader import reader_function, export_ome_tiff

import ome_types
from tifffile import imwrite, tiffcomment


# TODO:  depricate AICSImageReaderWrap
@dataclass
class AICSImageReaderWrap:
    """
    Simple dataclass wrapper for the AICSImage output to prepare for imprting to our bioim class
    TODO: make a nice reppr
    """

    name: str
    image: np.ndarray
    meta: Dict[str, Any]
    raw_meta: Tuple[Dict[str, Any], Union[Dict[str, Any], List]]

    def __init__(self, name: str, image: np.ndarray, meta: Dict[str, Any]):
        self.name = name
        self.image = image
        self.meta = meta
        self.raw_meta = get_raw_meta_data(meta)


def save_parameters(out_p, img_name, out_path) -> str:
    """
    #  out_p: defaultdict,
    # img_name: str,
    # out_path: types.PathLike,
    """
    out_name = str(out_path) + "/" + img_name + "_params.pkl"
    with open(out_name, "wb") as f:
        pickle.dump(out_p, f)
    return out_name


def load_parameters(img_name, out_path) -> defaultdict:
    out_name = str(out_path) + "/" + img_name + "_params.pkl"
    with open(out_name, "rb") as f:
        x = pickle.load(f)
    return x


def export_ndarray(data_in, img_name, out_path) -> str:
    """
    #  data_in: types.ArrayLike,
    #  meta_in: dict,
    # img_name: types.PathLike,
    # out_path: types.PathLike,
    # curr_chan: int
    # assumes a single image
    """

    out_name = out_path + img_name + ".npy"
    data_in.tofile(out_name)
    return out_name


def export_infer_organelles(img_out, layer_names, meta_dict, data_root_path):
    # get some top-level info about the RAW data
    channel_names = meta_dict["name"]
    img = meta_dict["metadata"]["aicsimage"]
    scale = meta_dict["scale"]
    channel_axis = meta_dict["channel_axis"]
    img_name = meta_dict["file_name"]
    # add params to metadata
    meta_dict["layer_names"] = layer_names
    out_path = data_root_path / "inferred_objects"
    img_name_out = "binarized_" + img_name.split("/")[-1].split(".")[0]

    out_file_n = export_ome_tiff(img_out, meta_dict, img_name_out, str(out_path) + "/", layer_names)
    print(f"saved file: {out_file_n}")
    return out_file_n


def append_ome_metadata(filename, meta_add):
    filename = "test.ome.tif"

    imwrite(
        filename,
        np.random.randint(0, 1023, (4, 256, 256, 3), "uint16"),
        bigtiff=True,
        photometric="RGB",
        tile=(64, 64),
        metadata={
            "axes": "ZYXS",
            "SignificantBits": 10,
            "Plane": {"PositionZ": [0.0, 1.0, 2.0, 3.0]},
        },
    )

    ome_xml = tiffcomment(filename)
    ome = ome_types.from_xml(ome_xml)
    ome.images[0].description = "Image 0 description"
    ome_xml = ome.to_xml()
    tiffcomment(filename, ome_xml)


### UTILS
def etree_to_dict(t):
    """
    etree dumper from stackoverflow
    """
    d = {t.tag: {} if t.attrib else None}
    children = list(t)
    if children:
        dd = defaultdict(list)
        for dc in map(etree_to_dict, children):
            for k, v in dc.items():
                dd[k].append(v)
        d = {t.tag: {k: v[0] if len(v) == 1 else v for k, v in dd.items()}}
    if t.attrib:
        d[t.tag].update(("@" + k, v) for k, v in t.attrib.items())
    if t.text:
        text = t.text.strip()
        if children or t.attrib:
            if text:
                d[t.tag]["#text"] = text
        else:
            d[t.tag] = text
    return d


def get_raw_meta_data(meta_dict):
    """
    not sure why the linux backend works for ome... need to solve
    """
    curr_platform = system()

    if curr_platform == "Linux":
        raw_meta_data = meta_dict["metadata"]["raw_image_metadata"].dict()
        ome_types = meta_dict["metadata"]["ome_types"]
    elif curr_platform == "Darwin":
        raw_meta_data = meta_dict["metadata"]["raw_image_metadata"]
        ome_types = []
    else:
        raw_meta_data = meta_dict["metadata"]["raw_image_metadata"]
        ome_types = []
        print(f"warning: platform = '{curr_platform}' is untested")
    return (raw_meta_data, ome_types)


# TODO:  refactor this and napari plugin so napari_aicsimageio is not a dependency
# can then export to the organelle-segmenter-npe2 plugin
def read_input_image(image_name):
    """
    send output from napari aiscioimage reader wrapped in dataclass
    """
    data_out, meta_out, layer_type = reader_function(image_name)[0]
    return AICSImageReaderWrap(image_name, data_out, meta_out)


def read_czi_image(image_name):
    """
    return output from napari aiscioimage reader
    """
    data_out, meta_out, layer_type = reader_function(image_name)[0]

    meta_out["file_name"] = image_name
    return (data_out, meta_out)


# function to collect all the
def list_image_files(data_folder: Path, file_type: str) -> List:
    """
    get a list of all the filetypes
    TODO: aics has cleaner functions than this "lambda"
    """
    return [os.path.join(data_folder, f_name) for f_name in os.listdir(data_folder) if f_name.endswith(file_type)]
