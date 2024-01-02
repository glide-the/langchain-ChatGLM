from typing import Optional, Any

from fastapi import (APIRouter,
                     FastAPI,
                     HTTPException,
                     Response,
                     Request,
                     )
from configs import (logger)
from openai_plugins.callback.bootstrap import Bootstrap
import inspect
import pprint
from uvicorn import Config, Server
import xoscar as xo
from fastapi.middleware.cors import CORSMiddleware
from openai_plugins.publish.core.deploy_adapter_publish_actor import ProfileEndpointPublishActor
from starlette.responses import JSONResponse as StarletteJSONResponse
import multiprocessing as mp
from openai_plugins.utils import json_dumps


class JSONResponse(StarletteJSONResponse):
    def render(self, content: Any) -> bytes:
        return json_dumps(content)


class RESTFulBootstrapBaseWeb(Bootstrap):
    """
    Bootstrap Server Lifecycle
    """

    def __init__(self, publish_address: str, host: str, port: int):
        super().__init__()
        self._publish_address = publish_address
        self._host = host
        self._port = port
        self._publish_ref = None
        self._router = APIRouter()
        self._app = FastAPI()

    @classmethod
    def from_config(cls, cfg=None):
        publish_address = cfg.get("publish_address")
        return cls(publish_address=publish_address)

    @staticmethod
    def handle_request_limit_error(e: Exception):
        if "Rate limit reached" in str(e):
            raise HTTPException(status_code=429, detail=str(e))

    async def _get_publish_ref(self) -> xo.ActorRefType[ProfileEndpointPublishActor]:
        if self._publish_ref is None:
            self._publish_ref = await xo.actor_ref(
                address=self._publish_address, uid=ProfileEndpointPublishActor.uid()
            )
        return self._publish_ref

    def serve(self, logging_conf: Optional[dict] = None):
        self._app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        self._router.add_api_route("/status", self.get_status, methods=["GET"])
        self._router.add_api_route("/v1/list_plugins", self.list_plugins, methods=["GET"])
        self._router.add_api_route("/v1/launch_subscribe", self.launch_subscribe, methods=["POST"])
        self._router.add_api_route(
            "/v1/launch_subscribe/{plugins_name}", self.describe_adapter, methods=["GET"]
        )

        self._router.add_api_route(
            "/v1/launch_subscribe/{plugins_name}", self.terminate_subscribe, methods=["DELETE"]
        )

        self._router.add_api_route(
            "/v1/launch_subscribe/{plugins_name}/start", self.start, methods=["POST"]
        )

        self._router.add_api_route(
            "/v1/launch_subscribe/{plugins_name}/stop", self.stop, methods=["POST"]
        )

        self._router.add_api_route(
            "/v1/launch_subscribe/{plugins_name}/start_model/{new_model_name}",
            self.start_model,
            methods=["POST"]
        )

        self._router.add_api_route(
            "/v1/launch_subscribe/{plugins_name}/stop_model/{model_name}",
            self.stop_model,
            methods=["POST"]
        )

        self._router.add_api_route(
            "/v1/launch_subscribe/{plugins_name}/replace_model/{model_name}/{new_model_name}",
            self.replace_model,
            methods=["POST"]
        )

        self._router.add_api_route(
            "/v1/launch_subscribe/{plugins_name}/list_running_models",
            self.list_running_models,
            methods=["GET"]
        )

        self._router.add_api_route(
            "/v1/launch_subscribe/{plugins_name}/get_model_config/{model_name}",
            self.get_model_config,
            methods=["GET"]
        )

        self._app.include_router(self._router)

        # Check all the routes returns Response.
        # This is to avoid `jsonable_encoder` performance issue:
        # https://github.com/xorbitsai/inference/issues/647
        invalid_routes = []
        try:
            for router in self._router.routes:
                return_annotation = router.endpoint.__annotations__.get("return")
                if not inspect.isclass(return_annotation) or not issubclass(
                        return_annotation, Response
                ):
                    invalid_routes.append(
                        (router.path, router.endpoint, return_annotation)
                    )
        except Exception:
            pass  # In case that some Python version does not have __annotations__
        if invalid_routes:
            raise Exception(
                f"The return value type of the following routes is not Response:\n"
                f"{pprint.pformat(invalid_routes)}"
            )

        config = Config(
            app=self._app, host=self._host, port=self._port, log_config=logging_conf
        )
        server = Server(config)
        server.run()

    async def get_status(self) -> JSONResponse:
        try:
            status = await (await self._get_publish_ref()).get_status()
            return JSONResponse(content={"status": status})
        except Exception as e:
            logger.error(str(e), exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))

    async def list_plugins(self) -> JSONResponse:
        try:
            plugins_list = await (await self._get_publish_ref()).list_plugins()
            return JSONResponse(content={"plugins_list": plugins_list})
        except Exception as e:
            logger.error(str(e), exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))

    async def launch_subscribe(self, request: Request) -> JSONResponse:
        payload = await request.json()
        plugins_name = payload.get("plugins_name")
        request_limits = payload.get("request_limits", None)
        if plugins_name is None:
            raise HTTPException(
                status_code=400,
                detail="Invalid input. Please specify the plugins_name",
            )

        try:

            plugins_name = await (await self._get_publish_ref()).launch_subscribe(
                plugins_name=plugins_name,
                request_limits=request_limits,
            )

            return JSONResponse(content={"plugins_name": plugins_name})
        except Exception as e:
            logger.error(str(e), exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))

    async def describe_adapter(self, plugins_name: str) -> JSONResponse:
        try:
            adapter_description = await (await self._get_publish_ref()).describe_adapter(plugins_name)
            return JSONResponse(content={"adapter_description": adapter_description})
        except Exception as e:
            logger.error(str(e), exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))

    async def terminate_subscribe(self, plugins_name: str) -> JSONResponse:
        try:
            await (await self._get_publish_ref()).terminate_subscribe(plugins_name)
            return JSONResponse(content={"plugins_name": plugins_name})
        except Exception as e:
            logger.error(str(e), exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))

    async def start(self, plugins_name: str) -> JSONResponse:
        try:
            adapter = await (await self._get_publish_ref()).get_adapter(plugins_name)
            await adapter.start()
            return JSONResponse(content={"plugins_name": plugins_name})
        except Exception as e:
            logger.error(str(e), exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))

    async def stop(self, plugins_name: str) -> JSONResponse:
        try:
            adapter = await (await self._get_publish_ref()).get_adapter(plugins_name)
            await adapter.stop()
            return JSONResponse(content={"plugins_name": plugins_name})
        except Exception as e:
            logger.error(str(e), exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))

    async def start_model(self, plugins_name: str, new_model_name: str) -> JSONResponse:
        try:
            adapter = await (await self._get_publish_ref()).get_adapter(plugins_name)
            await adapter.start_model(new_model_name=new_model_name)
            return JSONResponse(content={"plugins_name": plugins_name})
        except Exception as e:
            logger.error(str(e), exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))

    async def stop_model(self, plugins_name: str, model_name: str) -> JSONResponse:
        try:
            adapter = await (await self._get_publish_ref()).get_adapter(plugins_name)
            await adapter.stop_model(model_name=model_name)
            return JSONResponse(content={"plugins_name": plugins_name})
        except Exception as e:
            logger.error(str(e), exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))

    async def replace_model(self, plugins_name: str, model_name: str, new_model_name: str) -> JSONResponse:
        try:
            adapter = await (await self._get_publish_ref()).get_adapter(plugins_name)
            await adapter.replace_model(model_name=model_name, new_model_name=new_model_name)
            return JSONResponse(content={"plugins_name": plugins_name})
        except Exception as e:
            logger.error(str(e), exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))

    async def list_running_models(self, plugins_name: str) -> JSONResponse:
        try:
            adapter = await (await self._get_publish_ref()).get_adapter(plugins_name)
            data = await adapter.list_running_models()
            return JSONResponse(content={"data": data})
        except Exception as e:
            logger.error(str(e), exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))

    async def get_model_config(self, plugins_name: str, model_name: str) -> JSONResponse:
        try:
            adapter = await (await self._get_publish_ref()).get_adapter(plugins_name)
            data = await adapter.get_model_config(model_name=model_name)
            return JSONResponse(content={"data": data})
        except Exception as e:
            logger.error(str(e), exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))


def run(
        publish_address: str, host: str, port: int, logging_conf: Optional[dict] = None
):
    logger.info(f"Starting openai plugins at endpoint: http://{host}:{port}")
    try:
        api = RESTFulBootstrapBaseWeb(publish_address=publish_address, host=host, port=port)
        api.serve(logging_conf=logging_conf)
    except SystemExit:
        logger.warning("Failed to create socket with port %d", port)
        raise


def run_in_subprocess(
        publish_address: str, host: str, port: int, logging_conf: Optional[dict] = None
) -> mp.Process:
    p = mp.Process(
        target=run, args=(publish_address, host, port, logging_conf)
    )
    p.daemon = True
    p.start()
    return p
