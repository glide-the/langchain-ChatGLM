from multiprocessing import Process
from typing import List
from configs import (
    logger,
)
from launch_module import shared_cmd_options
from openai_plugins.core.adapter import LLMWorkerInfo
from openai_plugins.core.control import ControlAdapter

import time
from datetime import datetime
import os
import sys

# 为了能使用fastchat_wrapper.py中的函数，需要将当前目录加入到sys.path中
root_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(root_dir)
import fastchat_process_dict
from fastchat_wrapper import run_model_worker


class FastChatControlAdapter(ControlAdapter):

    def __init__(self, state_dict: dict = None):
        super().__init__(state_dict=state_dict)

    def class_name(self) -> str:
        """Get class name."""
        return self.__name__

    def start_model(self, new_model_name):
        logger.info(f"准备启动新模型进程：{new_model_name}")
        e = self.processesInfo.mp_manager.Event()
        process = Process(
            target=run_model_worker,
            name=f"model_worker - {new_model_name}",
            kwargs=dict(model_name=new_model_name,
                        controller_address=shared_cmd_options.cmd_opts.controller_address,
                        log_level=self.processesInfo.log_level,
                        q=self.processesInfo.queue,
                        started_event=e),
            daemon=True,
        )
        process.start()
        process.name = f"{process.name} ({process.pid})"
        fastchat_process_dict.processes["model_worker"][new_model_name] = process
        e.wait()
        logger.info(f"成功启动新模型进程：{new_model_name}")

    def stop_model(self, model_name: str):
        if process := fastchat_process_dict.processes["model_worker"].get(model_name):
            time.sleep(1)
            process.terminate()
            process.join()
            logger.info(f"停止模型进程：{model_name}")
        else:
            logger.error(f"未找到模型进程：{model_name}")

    def replace_model(self, pid: str, model_name: str, new_model_name: str):
        e = self.processesInfo.mp_manager.Event()
        if process := fastchat_process_dict.processes["model_worker"].pop(model_name, None):
            logger.info(f"停止模型进程：{model_name}")
            start_time = datetime.now()
            time.sleep(1)
            process.terminate()
            process.join()
            process = Process(
                target=run_model_worker,
                name=f"model_worker - {new_model_name}",
                kwargs=dict(model_name=new_model_name,
                            controller_address=shared_cmd_options.cmd_opts.controller_address,
                            log_level=self.processesInfo.log_level,
                            q=self.processesInfo.queue,
                            started_event=e),
                daemon=True,
            )
            process.start()
            process.name = f"{process.name} ({process.pid})"
            fastchat_process_dict.processes["model_worker"][new_model_name] = process
            e.wait()
            timing = datetime.now() - start_time
            logger.info(f"成功启动新模型进程：{new_model_name}。用时：{timing}。")
        else:
            logger.error(f"未找到模型进程：{model_name}")

    @classmethod
    def from_config(cls, cfg=None):
        _state_dict = {
            "controller_name": "fastchat",
            "controller_version": "0.0.1",
            "controller_description": "fastchat controller",
            "controller_author": "fastchat"
        }
        state_dict = cfg.get("state_dict", {})
        if state_dict is not None and _state_dict is not None:
            _state_dict = {**state_dict, **_state_dict}
        else:
            # 处理其中一个或两者都为 None 的情况
            _state_dict = state_dict or _state_dict or {}

        return cls(state_dict=_state_dict)
