import uuid

from fastapi import Body
from configs import logger, log_verbose, LLM_MODELS, HTTPX_DEFAULT_TIMEOUT
from server.utils import (BaseResponse, fschat_controller_address, list_config_llm_models,
                          get_httpx_client, get_model_worker_config)
from typing import List
import launch_module.launch_mp_queue as launch_mp_queue


def list_running_models(
        controller_address: str = Body(None, description="Fastchat controller服务器地址",
                                       examples=[fschat_controller_address()]),
        placeholder: str = Body(None, description="该参数未使用，占位用"),
) -> BaseResponse:
    '''
    从fastchat controller获取已加载模型列表及其配置项
    '''
    try:
        controller_address = controller_address or fschat_controller_address()
        with get_httpx_client() as client:
            r = client.post(controller_address + "/list_models")
            models = r.json()["models"]
            data = {m: get_model_config(m).data for m in models}
            return BaseResponse(data=data)
    except Exception as e:
        logger.error(f'{e.__class__.__name__}: {e}',
                     exc_info=e if log_verbose else None)
        return BaseResponse(
            code=500,
            data={},
            msg=f"failed to get available models from controller: {controller_address}。错误信息是： {e}")


def list_config_models(
        types: List[str] = Body(["local", "online"], description="模型配置项类别，如local, online, worker"),
        placeholder: str = Body(None, description="占位用，无实际效果")
) -> BaseResponse:
    '''
    从本地获取configs中配置的模型列表
    '''
    data = {}
    for type, models in list_config_llm_models().items():
        if type in types:
            data[type] = {m: get_model_config(m).data for m in models}
    return BaseResponse(data=data)


def get_model_config(
        model_name: str = Body(description="配置中LLM模型的名称"),
        placeholder: str = Body(None, description="占位用，无实际效果")
) -> BaseResponse:
    '''
    获取LLM模型配置项（合并后的）
    '''
    config = {}
    # 删除ONLINE_MODEL配置中的敏感信息
    for k, v in get_model_worker_config(model_name=model_name).items():
        if not (k == "worker_class"
                or "key" in k.lower()
                or "secret" in k.lower()
                or k.lower().endswith("id")):
            config[k] = v

    return BaseResponse(data=config)


def stop_llm_model(
        plugins_name: str = Body(..., description="当前运行插件", examples=["fschat"]),
        model_name: str = Body(..., description="要停止的LLM模型名称", examples=[LLM_MODELS[0]])
) -> BaseResponse:
    """
    向信号队列发送停止LLM模型的信号
    """
    # 创建一个控制标志，用于判断新的事件是否已经被处理
    new_pid = uuid.uuid4().hex
    launch_mp_queue.shared_queue.put([plugins_name, model_name, "stop", None, new_pid])
    # 等待事件处理完成
    while True:
        cmd = launch_mp_queue.shared_completed_queue.get()

        plugins_name, model_name, command, new_model_name, pid = cmd
        if command == "stopped" and new_pid == pid:
            break
        else:
            # 如果不是当前进程的事件，重新放回队列
            launch_mp_queue.shared_completed_queue.put(cmd)
    return BaseResponse(data='done')


def change_llm_model(
        plugins_name: str = Body(..., description="当前运行插件", examples=["fschat"]),
        model_name: str = Body(..., description="当前运行模型", examples=[LLM_MODELS[0]]),
        new_model_name: str = Body(..., description="要切换的新模型", examples=[LLM_MODELS[0]])
):
    """
    向信号队列发送切换LLM模型的信号，使用信号控制模型是否已经切换完成
    """
    # 创建一个控制标志，用于判断新的事件是否已经被处理
    new_pid = uuid.uuid4().hex
    launch_mp_queue.shared_queue.put([plugins_name, model_name, "replace", new_model_name, new_pid])
    # 等待事件处理完成
    while True:
        cmd = launch_mp_queue.shared_completed_queue.get()

        plugins_name, model_name, command, new_model_name, pid = cmd
        if command == "replaced" and new_pid == pid:
            break
        else:
            # 如果不是当前进程的事件，重新放回队列
            launch_mp_queue.shared_completed_queue.put(cmd)
    return BaseResponse(data='done')


def list_search_engines() -> BaseResponse:
    from server.chat.search_engine_chat import SEARCH_ENGINES

    return BaseResponse(data=list(SEARCH_ENGINES))
