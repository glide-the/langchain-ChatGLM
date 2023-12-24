from configs import (
    LLM_MODELS,
)
import argparse

parser = argparse.ArgumentParser()
parser.add_argument(
    "-a",
    "--all-webui",
    action="store_true",
    help="run fastchat's controller/openai_api/model_worker servers, run api.py and webui.py",
    dest="all_webui",
)
parser.add_argument(
    "--all-api",
    action="store_true",
    help="run fastchat's controller/openai_api/model_worker servers, run api.py",
    dest="all_api",
)
parser.add_argument(
    "--llm-api",
    action="store_true",
    help="run fastchat's controller/openai_api/model_worker servers",
    dest="llm_api",
)
parser.add_argument(
    "-o",
    "--openai-api",
    action="store_true",
    help="run fastchat's controller/openai_api servers",
    dest="openai_api",
)
parser.add_argument(
    "-m",
    "--model-worker",
    action="store_true",
    help="run fastchat's model_worker server with specified model name. "
         "specify --model-name if not using default LLM_MODELS",
    dest="model_worker",
)
parser.add_argument(
    "-n",
    "--model-name",
    type=str,
    nargs="+",
    default=LLM_MODELS,
    help="specify model name for model worker. "
         "add addition names with space seperated to start multiple model workers.",
    dest="model_name",
)
parser.add_argument(
    "-c",
    "--controller",
    type=str,
    help="specify controller address the worker is registered to. default is FSCHAT_CONTROLLER",
    dest="controller_address",
)
parser.add_argument(
    "--api",
    action="store_true",
    help="run api.py server",
    dest="api",
)
parser.add_argument(
    "-p",
    "--api-worker",
    action="store_true",
    help="run online model api such as zhipuai",
    dest="api_worker",
)
parser.add_argument(
    "-w",
    "--webui",
    action="store_true",
    help="run webui.py server",
    dest="webui",
)
parser.add_argument(
    "-q",
    "--quiet",
    action="store_true",
    help="减少fastchat服务log信息",
    dest="quiet",
)
parser.add_argument(
    "-i",
    "--lite",
    action="store_true",
    help="以Lite模式运行：仅支持在线API的LLM对话、搜索引擎对话",
    dest="lite",
)
