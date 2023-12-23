
from common.registry import registry
import os


def init_folder_config():

    root_dir = os.path.dirname(os.path.abspath(__file__))

    registry.register_path("base_library_root", root_dir)

    registry.register_path("openai_plugins_folder", os.path.join(root_dir, "openai"))

