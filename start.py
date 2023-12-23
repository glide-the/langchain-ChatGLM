from openai_plugins import openai_components_plugins_register, openai_install_plugins_load
import init_folder_config



def main():
    init_folder_config.init_folder_config()
    openai_components_plugins_register()
    openai_install_plugins_load()



if __name__ == '__main__':
    main()
