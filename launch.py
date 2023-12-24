from openai_plugins import (openai_components_plugins_register,
                            openai_install_plugins_load)
from openai_plugins.adapter.adapter import ProcessesInfo
from openai_plugins.callback import (callback_map)
import asyncio
import multiprocessing as mp
import sys
from multiprocessing import Process
from launch_module.launch_utils import dump_server_info
from server.knowledge_base.migrate import create_tables
import init_folder_config
from launch_module import launch_utils
from configs import (
    LOG_PATH,
    log_verbose,
    logger,
)

args = launch_utils.args


async def main():
    init_folder_config.init_folder_config()
    openai_components_plugins_register()
    openai_install_plugins_load()

    print(callback_map.callbacks_controller_adapter)
    print(callback_map.callbacks_application_adapter)

    import signal

    def handler(signalname):
        """
        Python 3.9 has `signal.strsignal(signalnum)` so this closure would not be needed.
        Also, 3.8 includes `signal.valid_signals()` that can be used to create a mapping for the same purpose.
        """

        def f(signal_received, frame):
            raise KeyboardInterrupt(f"{signalname} received")

        return f

    # This will be inherited by the child process if it is forked (not spawned)
    signal.signal(signal.SIGINT, handler("SIGINT"))
    signal.signal(signal.SIGTERM, handler("SIGTERM"))

    mp.set_start_method("spawn")
    manager = mp.Manager()
    run_mode = None

    queue = manager.Queue()

    if args.all_webui:
        args.openai_api = True
        args.model_worker = True
        args.api = True
        args.api_worker = True
        args.webui = True

    elif args.all_api:
        args.openai_api = True
        args.model_worker = True
        args.api = True
        args.api_worker = True
        args.webui = False

    elif args.llm_api:
        args.openai_api = True
        args.model_worker = True
        args.api_worker = True
        args.api = False
        args.webui = False

    if args.lite:
        args.model_worker = False
        run_mode = "lite"

    dump_server_info(args=args)

    if len(sys.argv) > 1:
        logger.info(f"正在启动服务：")
        logger.info(f"如需查看 llm_api 日志，请前往 {LOG_PATH}")

    processes = {}

    if args.quiet or not log_verbose:
        log_level = "ERROR"
    else:
        log_level = "INFO"

    api_started = manager.Event()
    if args.api:
        process = Process(
            target=launch_utils.run_api_server,
            name=f"API Server",
            kwargs=dict(started_event=api_started, run_mode=run_mode),
            daemon=True,
        )
        processes["api"] = process

    webui_started = manager.Event()
    if args.webui:
        process = Process(
            target=launch_utils.run_webui,
            name=f"WEBUI Server",
            kwargs=dict(started_event=webui_started, run_mode=run_mode),
            daemon=True,
        )
        processes["webui"] = process

    # openai_plugins 组件加载
    app_adapters = callback_map.callbacks_application_adapter.get_callbacks()
    for app_adapter in app_adapters:
        processesInfo = ProcessesInfo(
            model_name=args.model_name,
            controller_address=args.controller_address,
            log_level=log_level,
            queue=queue,
            mp_manager=manager,
        )

        app_adapter.init_processes(processesInfo=processesInfo)

    try:
        if p := processes.get("api"):
            p.start()
            p.name = f"{p.name} ({p.pid})"
            api_started.wait()  # 等待api.py启动完成

        if p := processes.get("webui"):
            p.start()
            p.name = f"{p.name} ({p.pid})"
            webui_started.wait()  # 等待webui.py启动完成

        # openai_plugins 组件启动
        try:
            for app_adapter in app_adapters:
                app_adapter.start()
        except Exception as e:
            logger.error(e)
            raise e


        dump_server_info(after_start=True, args=args)

        while True:
            cmd = queue.get()
            logger.info(f"收到切换模型的消息：{cmd}")

    except Exception as e:
        logger.error(e)
        logger.warning("Caught KeyboardInterrupt! Setting stop event...")
    finally:
        # Send SIGINT if process doesn't exit quickly enough, and kill it as last resort
        # .is_alive() also implicitly joins the process (good practice in linux)
        # while alive_procs := [p for p in processes.values() if p.is_alive()]:

        for p in processes.values():
            logger.warning("Sending SIGKILL to %s", p)
            # Queues and other inter-process communication primitives can break when
            # process is killed, but we don't care here

            if isinstance(p, dict):
                for process in p.values():
                    process.kill()
            else:
                p.kill()

        for p in processes.values():
            logger.info("Process status: %s", p)

if __name__ == "__main__":
    # 确保数据库表被创建
    create_tables()

    if sys.version_info < (3, 10):
        loop = asyncio.get_event_loop()
    else:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()

        asyncio.set_event_loop(loop)
    # 同步调用协程代码
    loop.run_until_complete(main())
