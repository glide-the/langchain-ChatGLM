
import os
import importlib.util
import time
from openai_plugins.callback import register_controller_adapter


def plugins_components_load(register_components_adapter,
                            plugins_name: str,
                            module_path: str,
                            endpoint_components_file: str,
                            components_adapter: str):
    """
    openai components模块 加载
    :param register_components_adapter:  components模块注册函数
    :param plugins_name: openai_plugins_list.json配置的plugins_name
    :param module_path:
    :param endpoint_components_file:
    :param components_adapter:
    :return:
    """

    def execute_script(script_path):
        module_name = os.path.splitext(script_path)[0]
        try:
            spec = importlib.util.spec_from_file_location(module_name, script_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return module
        except Exception as err:
            print(f"Failed to execute startup-script: {script_path} / {err}")
            raise err

    node_openai_components_load_times = []
    script_path = os.path.join(module_path, endpoint_components_file)
    if os.path.exists(script_path):
        time_before = time.perf_counter()
        try:
            module_plugins = execute_script(script_path)
            if module_plugins is None:
                node_openai_components_load_times.append((time.perf_counter() - time_before, module_path, False))

            if module_plugins is not None:

                # 判断模型是否存在components_adapter类
                if hasattr(module_plugins, components_adapter):
                    # 获取components_adapter类
                    components_adapter_class = getattr(module_plugins, components_adapter)
                    # 实例化components_adapter类
                    components_adapter_instance = components_adapter_class.from_config(cfg={})
                    # 注册components_adapter类
                    register_components_adapter(plugins_name=plugins_name, adapter=components_adapter_instance)
                    # 将模型的预加载时间和模型路径添加到node_prestartup_times列表中
                    node_openai_components_load_times.append((time.perf_counter() - time_before, module_path, True))
                else:
                    node_openai_components_load_times.append((time.perf_counter() - time_before, module_path, False))
        except Exception as e:
            print(f"Failed to load components_adapter: {components_adapter} / {e}")
            node_openai_components_load_times.append((time.perf_counter() - time_before, module_path, False))
    if len(node_openai_components_load_times) > 0:
        print(f"\nRegister times for { register_components_adapter.__name__}:")
        for n in sorted(node_openai_components_load_times):
            if n[2]:
                import_message = ""
            else:
                import_message = " (REGISTER FAILED)"
            print("{:6.1f} seconds{}:".format(n[0], import_message), n[1])
        print()

