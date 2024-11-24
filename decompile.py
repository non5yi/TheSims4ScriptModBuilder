import fnmatch
import multiprocessing
import os
import shutil
import string
import sys
from pathlib import Path
from subprocess import run
from zipfile import PyZipFile
from utils.constants import *
from utils.utils import create_directory, prepare_directory, clean_directory
from multiprocessing import Pool
import time


# copy the zip files
def copy_zip(src: string, dest: string):
    shutil.copytree(src, dest)


def unzip(src: string, dest: string):
    for file in os.listdir(src):
        if file.endswith('.zip'):
            PyZipFile(os.path.join(src, file)).extractall(
                os.path.join(dest, file.title().split('.')[0].lower()))


def decompile_worker(args):
    dest_path, src_file = args
    rv = run([uncompyle6, "-o", dest_path, src_file], text=True,
        capture_output=True)
    return [rv.returncode, rv.stderr]


def decompile(src: string):
    print('start decompiling files under: ' + src)
    start = time.time()

    # total = 0
    # success = 0
    todo = []

    for root, dirs, files in os.walk(src):
        for filename in fnmatch.filter(files, "*.pyc"):
            # print('.', end='') if success % 30 or success == 0 else print('.')  # next line
            # total += 1

            src_file_path = str(os.path.join(root, filename))
            relative_path = str(Path(root).relative_to(project_game_unzip_dir))
            dest_path = os.path.join(project_game_decompile_dir, relative_path)
            if not os.path.exists(dest_path):
                os.makedirs(dest_path)

            todo.append([dest_path, src_file_path])

    with Pool(num_decompilers) as pool:
        rv = pool.map(decompile_worker, todo)
        pool.close()
        pool.join()

    total = len(todo)
    success = sum([1 for x in rv if x[0] == 0 and not x[1]])

    elapsed = time.time() - start
    print("Finished decompilation under folder %s after %d secs." % (
        src, elapsed))
    print('Success rate: ' + str(round((success * 100) / total, 2)) + '%')
    if success * 100.0 / total < success_rate:
        sys.exit("Success rate is lower than %d%, exit." % success_rate)


def copy_files_and_unzip():
    # The Sims 4.app/Contents/Python generated.zip
    # The Sims 4.app/Contents/Data/Simulation/Gameplay -> base.zip, core.zip, simulation.zip
    prepare_directory(project_game_zip_dir)
    copy_zip(game_content_python,
        os.path.join(project_game_zip_dir, project_game_python))
    copy_zip(game_content_gameplay,
        os.path.join(project_game_zip_dir,project_game_gameplay))

    prepare_directory(project_game_unzip_dir)
    unzip(os.path.join(project_game_zip_dir, project_game_python),
        project_game_unzip_dir)
    unzip(os.path.join(project_game_zip_dir, project_game_gameplay),
        project_game_unzip_dir)


def run_decompile():
    for folder in [
        os.path.join(project_game_unzip_dir, x) for x in os.listdir(
            project_game_unzip_dir)]:
        decompile(folder)

def copy_folders_to_src():
    # The library folders that need to be copied for writing convenience.
    folders = [os.path.join("base", "lib"), "core", "simulation"]
    for folder in folders:
        src_folder = os.path.join(project_game_decompile_dir, folder)
        if folder == folders[0]:
            target_folder = os.path.join(project_src_dir, "lib")
        else:
            target_folder = os.path.join(project_src_dir, folder)
        clean_directory(target_folder)
        shutil.copytree(src_folder, target_folder,
                        ignore=shutil.ignore_patterns('*.pyc'))

def prepare():
    done = False
    while not done:
        try:
            create_directory(os.path.join(project_dir, 'game'))
            copy_files_and_unzip()

            prepare_directory(project_game_decompile_dir)
        except PermissionError:
            continue
        done = True
    return


if __name__ == '__main__':
    multiprocessing.freeze_support()
    prepare()
    run_decompile()
    copy_folders_to_src()
