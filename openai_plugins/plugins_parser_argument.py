# import os
# import importlib.util
#
# from modules import errors
#
# from modules import cmd_args, script_loading
# from modules.paths_internal import models_path, script_path, data_path, sd_configs_path, sd_default_config, sd_model_file, default_sd_model_file, extensions_dir, extensions_builtin_dir  # noqa: F401
#
# parser = cmd_args.parser
#
# script_loading.preload_extensions(extensions_dir, parser, extension_list=launch.list_extensions(launch.args.ui_settings_file))
# script_loading.preload_extensions(extensions_builtin_dir, parser)
#
# if os.environ.get('IGNORE_CMD_ARGS_ERRORS', None) is None:
#     cmd_opts = parser.parse_args()
# else:
#     cmd_opts, _ = parser.parse_known_args()
#
# cmd_opts.webui_is_non_local = any([cmd_opts.share, cmd_opts.listen, cmd_opts.ngrok, cmd_opts.server_name])
# cmd_opts.disable_extension_access = cmd_opts.webui_is_non_local and not cmd_opts.enable_insecure_extension_access
#
#
#
# def load_module(path):
#     module_spec = importlib.util.spec_from_file_location(os.path.basename(path), path)
#     module = importlib.util.module_from_spec(module_spec)
#     module_spec.loader.exec_module(module)
#
#     return module
#
#
# def register_parser_argument_extensions(extensions_dir, parser, parser_argument_file, extension_list=None):
#     if not os.path.isdir(extensions_dir):
#         return
#
#     extensions = extension_list if extension_list is not None else os.listdir(extensions_dir)
#     for dirname in sorted(extensions):
#         parser_argument_script = os.path.join(extensions_dir, dirname, parser_argument_file)
#         if not os.path.isfile(parser_argument_script):
#             continue
#
#         try:
#             module = load_module(parser_argument_script)
#             if hasattr(module, 'preload'):
#                 module.preload(parser)
#
#         except Exception:
#             errors.report(f"Error running preload() for {preload_script}", exc_info=True)
