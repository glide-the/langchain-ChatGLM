from typing import Dict, List

from openai_plugins.adapter.adapter import ProcessesInfo
from openai_plugins.application import ApplicationAdapter
from launch_module import shared_cmd_options
from multiprocessing import Process, Manager
import multiprocessing as mp
from configs import (
    logger,
    FSCHAT_MODEL_WORKERS,
)
import time
from server.utils import (get_httpx_client, fschat_controller_address, set_httpx_config,
                          fschat_model_worker_address, get_model_worker_config)
from datetime import datetime
import os
import sys

# 为了能使用fastchat_wrapper.py中的函数，需要将当前目录加入到sys.path中
root_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(root_dir)

from fastchat_wrapper import run_controller, run_model_worker, run_openai_api
import fastchat_process_dict


class FastChatApplicationAdapter(ApplicationAdapter):
    processesInfo: ProcessesInfo = None
    controller_started: mp.Event = None
    model_worker_started: List[mp.Event] = []

    def __init__(self, state_dict: dict = None):

        super().__init__(state_dict=state_dict)

    @classmethod
    def from_config(cls, cfg=None):
        _state_dict = {
            "application_name": "fastchat",
            "application_version": "0.0.1",
            "application_description": "fastchat application",
            "application_author": "fastchat"
        }
        state_dict = cfg.get("state_dict", {})
        if state_dict is not None and _state_dict is not None:
            _state_dict = {**state_dict, **_state_dict}
        else:
            # 处理其中一个或两者都为 None 的情况
            _state_dict = state_dict or _state_dict or {}
        return cls(state_dict=_state_dict)

    def init_processes(self, processesInfo: ProcessesInfo):

        self.processesInfo = processesInfo

        if shared_cmd_options.cmd_opts.all_webui:
            shared_cmd_options.cmd_opts.openai_api = True
            shared_cmd_options.cmd_opts.model_worker = True
            shared_cmd_options.cmd_opts.api_worker = True

        elif shared_cmd_options.cmd_opts.all_api:
            shared_cmd_options.cmd_opts.openai_api = True
            shared_cmd_options.cmd_opts.model_worker = True
            shared_cmd_options.cmd_opts.api_worker = True

        elif shared_cmd_options.cmd_opts.llm_api:
            shared_cmd_options.cmd_opts.openai_api = True
            shared_cmd_options.cmd_opts.model_worker = True
            shared_cmd_options.cmd_opts.api_worker = True

        if shared_cmd_options.cmd_opts.lite:
            shared_cmd_options.cmd_opts.model_worker = False

        fastchat_process_dict.processes = {"online_api": {}, "model_worker": {}}
        self.controller_started = processesInfo.mp_manager.Event()
        if shared_cmd_options.cmd_opts.openai_api:
            process = Process(
                target=run_controller,
                name=f"controller",
                kwargs=dict(log_level=processesInfo.log_level, started_event=self.controller_started),
                daemon=True,
            )
            fastchat_process_dict.processes["controller"] = process

            process = Process(
                target=run_openai_api,
                name=f"openai_api",
                daemon=True,
            )
            fastchat_process_dict.processes["openai_api"] = process

        if shared_cmd_options.cmd_opts.model_worker:
            for model_name in shared_cmd_options.cmd_opts.model_name:
                config = get_model_worker_config(model_name)
                if not config.get("online_api"):
                    e = processesInfo.mp_manager.Event()
                    self.model_worker_started.append(e)
                    process = Process(
                        target=run_model_worker,
                        name=f"model_worker - {model_name}",
                        kwargs=dict(model_name=model_name,
                                    controller_address=shared_cmd_options.cmd_opts.controller_address,
                                    log_level=processesInfo.log_level,
                                    q=processesInfo.queue,
                                    started_event=e),
                        daemon=True,
                    )
                    fastchat_process_dict.processes["model_worker"][model_name] = process

        if shared_cmd_options.cmd_opts.api_worker:
            for model_name in shared_cmd_options.cmd_opts.model_name:
                config = get_model_worker_config(model_name)
                if (config.get("online_api")
                        and config.get("worker_class")
                        and model_name in FSCHAT_MODEL_WORKERS):
                    e = processesInfo.mp_manager.Event()
                    self.model_worker_started.append(e)
                    process = Process(
                        target=run_model_worker,
                        name=f"api_worker - {model_name}",
                        kwargs=dict(model_name=model_name,
                                    controller_address=shared_cmd_options.cmd_opts.controller_address,
                                    log_level=processesInfo.log_level,
                                    q=processesInfo.queue,
                                    started_event=e),
                        daemon=True,
                    )
                    fastchat_process_dict.processes["online_api"][model_name] = process

    def start(self):
        # 保证任务收到SIGINT后，能够正常退出
        if p := fastchat_process_dict.processes.get("controller"):
            p.start()
            p.name = f"{p.name} ({p.pid})"
            self.controller_started.wait()  # 等待controller启动完成

        if p := fastchat_process_dict.processes.get("openai_api"):
            p.start()
            p.name = f"{p.name} ({p.pid})"

        for n, p in fastchat_process_dict.processes.get("model_worker", {}).items():
            p.start()
            p.name = f"{p.name} ({p.pid})"

        for n, p in fastchat_process_dict.processes.get("online_api", []).items():
            p.start()
            p.name = f"{p.name} ({p.pid})"

        # 等待所有model_worker启动完成
        for e in self.model_worker_started:
            e.wait()

    def stop(self):
        for p in fastchat_process_dict.processes.values():
            logger.warning("Sending SIGKILL to %s", p)
            # Queues and other inter-process communication primitives can break when
            # process is killed, but we don't care here

            if isinstance(p, dict):
                for process in p.values():
                    process.kill()
            else:
                p.kill()

        for p in fastchat_process_dict.processes.values():
            logger.info("Process status: %s", p)
