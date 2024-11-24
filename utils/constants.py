import configparser
import os

config = configparser.ConfigParser()
config.read('config.ini')

project_dir = config['Directory']['ProjectDir']
game_content_dir = config['Directory']['Sims4GameContentDir']
mods_dir = config['Directory']['Sims4ModDir']
uncompyle6 = config['Dependency']['Uncompyle6Path']
mod_name = config['Mod']['Name']
num_decompilers = config.getint('Dependency','workers')
success_rate = config.getint('Dependency', 'successRate')

game_content_python = game_content_dir + config['Directory']['GameContentPython']
game_content_gameplay = os.path.join(game_content_dir, "Data",
    "Simulation", "GamePlay")

project_game_zip_dir = os.path.join(project_dir, "game", "zip")
project_game_unzip_dir = os.path.join(project_dir, "game", "unzip")
project_game_decompile_dir = os.path.join(project_dir, "game", "decompile")
project_game_python = "python"
project_game_gameplay = "gameplay"
project_build_dir = os.path.join(project_dir, "build")
project_build_compile_dir = os.path.join(project_build_dir, "compile")
project_src_dir = os.path.join(project_dir, "src")
