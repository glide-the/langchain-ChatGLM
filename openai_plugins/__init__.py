from common.registry import registry
import os

from openai_plugins.enginer_system import (openai_components_plugins_register, openai_install_plugins_load,
                                           openai_plugins_config)
root_dir = os.path.dirname(os.path.abspath(__file__))
registry.register_path("openai_plugins_library_root", root_dir)


__all__ = [
    "openai_components_plugins_register",
    "openai_install_plugins_load",
    "openai_plugins_config"
]
