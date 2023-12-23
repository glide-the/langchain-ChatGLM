
class OpenAIPluginsConfig:
    def __init__(self):
        self.plugins_name = ""
        self.endpoint_host = ""
        self.install_file = "install.py"
        self.application_file = "app.py"
        self.application_class = "ApplicationAdapter"
        self.endpoint_controller_file = "controller_callbacks.py"
        self.endpoint_controller_class = "ControllerAdapter"
        self.openai_plugins_module_path = ""
        self.openai_plugins_content = ""

