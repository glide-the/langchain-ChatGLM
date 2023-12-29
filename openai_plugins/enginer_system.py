"""

"""
from typing import List

from openai_plugins.plugins_install import run_install_script
from openai_plugins.plugins_config import OpenAIPluginsConfig
from openai_plugins.plugins_components import plugins_components_load
from openai_plugins.callback import (register_controller_adapter,
                                     register_application_adapter,
                                     register_profile_endpoint_adapter)
from common.registry import registry
import os


def get_openai_plugins_json() -> List[OpenAIPluginsConfig]:
    possible_modules = os.listdir(registry.get_path("openai_plugins_folder"))

    for possible_module in possible_modules:
        module_path = os.path.join(registry.get_path("openai_plugins_folder"), possible_module)
        if os.path.isfile(module_path) or module_path.endswith(".disabled") or module_path == "__pycache__":
            continue
        openai_plugins_list = []
        # 读取openai-plugins-list.json文件，
        openai_plugins_json = os.path.join(module_path, "openai_plugins.json")
        if os.path.exists(openai_plugins_json):
            with open(openai_plugins_json, "r") as f:
                import json
                openai_plugins = OpenAIPluginsConfig()
                openai_plugins_content = json.load(f)
                openai_plugins.openai_plugins_module_path = module_path
                openai_plugins.openai_plugins_content = json.dumps(openai_plugins_content, indent=4, ensure_ascii=False)
                if "plugins_name" in openai_plugins_content:
                    openai_plugins.plugins_name = openai_plugins_content["plugins_name"]
                if "endpoint_host" in openai_plugins_content:
                    openai_plugins.endpoint_host = openai_plugins_content["endpoint_host"]
                if "install_file" in openai_plugins_content:
                    openai_plugins.install_file = openai_plugins_content["install_file"]
                if "application_file" in openai_plugins_content:
                    openai_plugins.application_file = openai_plugins_content["application_file"]
                if "application_class" in openai_plugins_content:
                    openai_plugins.application_class = openai_plugins_content["application_class"]
                if "endpoint_controller_file" in openai_plugins_content:
                    openai_plugins.endpoint_controller_file = openai_plugins_content["endpoint_controller_file"]
                if "endpoint_controller_class" in openai_plugins_content:
                    openai_plugins.endpoint_controller_class = openai_plugins_content["endpoint_controller_class"]
                if "profile_endpoint_file" in openai_plugins_content:
                    openai_plugins.profile_endpoint_file = openai_plugins_content["profile_endpoint_file"]
                if "profile_endpoint_class" in openai_plugins_content:
                    openai_plugins.profile_endpoint_class = openai_plugins_content["profile_endpoint_class"]

                openai_plugins_list.append(openai_plugins)

        return openai_plugins_list


def openai_plugins_config() -> List[str]:
    # 获取项目配置的openai-plugins-list.json文件中openai_plugins
    openai_plugins_list_json = os.path.join(registry.get_path("openai_plugins_library_root"),
                                            "openai-plugins-list.json")
    if os.path.exists(openai_plugins_list_json):
        with open(openai_plugins_list_json, "r") as f:
            import json
            openai_plugins_list = json.load(f)
            if 'openai_plugins' in openai_plugins_list:
                return openai_plugins_list['openai_plugins']

    return []


def openai_components_plugins_register():
    openai_plugins_list = get_openai_plugins_json()
    # 循环openai_plugins_list
    for openai_plugins in openai_plugins_list:

        module_path = openai_plugins.openai_plugins_module_path
        plugins_name = openai_plugins.plugins_name

        # 获取openai-plugins-list.json配置的endpoint_controller_file和endpoint_controller_class
        endpoint_controller_file = openai_plugins.endpoint_controller_file
        endpoint_controller_class = openai_plugins.endpoint_controller_class
        # 获取openai-plugins-list.json配置的endpoint_controller_file和endpoint_controller_class
        application_file = openai_plugins.application_file
        application_class = openai_plugins.application_class
        # 获取openai-plugins-list.json配置的profile_endpoint_file和profile_endpoint_class
        profile_endpoint_file = openai_plugins.profile_endpoint_file
        profile_endpoint_class = openai_plugins.profile_endpoint_class

        # 检查项目配置的openai-plugins-list.json文件中openai_plugins，是否包含当前模块
        openai_plugins_list = openai_plugins_config()

        # 判断openai_plugins_list['openai_plugins']列表中是否包含当前模块
        if plugins_name in openai_plugins_list:
            # 加载openai controller模块
            plugins_components_load(register_controller_adapter,
                                    plugins_name,
                                    module_path,
                                    endpoint_controller_file,
                                    endpoint_controller_class)
            # 加载openai application模块
            plugins_components_load(register_application_adapter,
                                    plugins_name,
                                    module_path,
                                    application_file,
                                    application_class)

            # 加载openai application模块
            plugins_components_load(register_profile_endpoint_adapter,
                                    plugins_name,
                                    module_path,
                                    profile_endpoint_file,
                                    profile_endpoint_class)


def openai_install_plugins_load():
    openai_plugins_list = get_openai_plugins_json()
    # 循环openai_plugins_list
    for openai_plugins in openai_plugins_list:

        plugins_name = openai_plugins.plugins_name
        module_path = openai_plugins.openai_plugins_module_path

        # 检查项目配置的openai-plugins-list.json文件中openai_plugins，是否包含当前模块
        openai_plugins_list_json = os.path.join(registry.get_path("openai_plugins_library_root"),
                                                "openai-plugins-list.json")
        if os.path.exists(openai_plugins_list_json):
            with open(openai_plugins_list_json, "r") as f:
                import json
                openai_plugins_list = json.load(f)
                if 'openai_plugins' in openai_plugins_list:
                    # 判断openai_plugins_list['openai_plugins']列表中是否包含当前模块
                    if plugins_name in openai_plugins_list['openai_plugins']:
                        # 运行install.py
                        print(f"{plugins_name} openai plugin install {openai_plugins.install_file}  running ...")
                        run_install_script(module_path, openai_plugins.install_file)
                        print(f"{plugins_name} openai plugin install {openai_plugins.install_file}  success ...")
