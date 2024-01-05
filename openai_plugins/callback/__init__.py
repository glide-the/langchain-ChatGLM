from openai_plugins.callback.core import (
    openai_plugin_loader,
    remove_controller_callbacks_adapter,
    remove_application_callbacks_adapter,
    register_controller_adapter,
    register_application_adapter,
    register_profile_endpoint_adapter,
    get_openai_plugin_loader
)
from openai_plugins.callback.bootstrap import bootstrap_register


# Compare this snippet from openai_plugins/callback/core.py:

__all__ = [
    "register_controller_adapter",
    "register_application_adapter",
    "register_profile_endpoint_adapter",
    "remove_controller_callbacks_adapter",
    "remove_application_callbacks_adapter",
    "openai_plugin_loader",
    "get_openai_plugin_loader"
]


# def init_bootstrap(bootstrap_cfg: dict = None):
#     bootstrap_register.register_bootstrap(OpenaiPluginsBootstrapBaseWeb, "openai_plugins_bootstrap")
#     openai_plugins_bootstrap = (bootstrap_register.get_bootstrap_class("openai_plugins_bootstrap")
#                                 .from_config(cfg=bootstrap_cfg))
#     openai_plugins_bootstrap.set_openai_plugin_loader(openai_plugin_loader)
