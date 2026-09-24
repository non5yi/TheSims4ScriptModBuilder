import fnmatch
import json
import multiprocessing
import os
import shutil
import string
import sys
from pathlib import Path
from subprocess import run
from subprocess import TimeoutExpired
import tempfile
from zipfile import PyZipFile
from utils.constants import *
from utils.utils import create_directory, prepare_directory
from multiprocessing import Pool
import time


def decompiler_tools():
    tools = [('uncompyle6', uncompyle6)]
    fallback = config.get('Dependency', 'Decompyle3Path', fallback='').strip()
    fallback = fallback or shutil.which('decompyle3')
    if not fallback:
        sibling = Path(uncompyle6).with_name('decompyle3.exe' if os.name == 'nt' else 'decompyle3')
        if sibling.is_file():
            fallback = str(sibling)
    if fallback:
        tools.append(('decompyle3', fallback))
    return tools


def validate_source(path):
    """Compile without executing; syntax validity is not semantic equivalence."""
    if not path.is_file():
        return 'Decompiler did not produce a .py file'
    try:
        source = path.read_bytes()
        if not source.strip() or not any(
                line.strip() and not line.lstrip().startswith(b'#')
                for line in source.splitlines()):
            return 'Empty or comment-only output requires manual review'
        compile(source, str(path), 'exec', dont_inherit=True)
    except (SyntaxError, ValueError, OSError) as exc:
        return '{}: {}'.format(type(exc).__name__, exc)
    return None


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
    relative = Path(src_file).resolve().relative_to(Path(project_game_unzip_dir).resolve())
    diagnostics = Path(project_dir) / 'game' / 'decompile_diagnostics' / relative
    result = {'source': str(src_file), 'validated': False, 'tool': None, 'attempts': []}
    timeout = config.getint('Dependency', 'decompileTimeout', fallback=120)
    for name, executable in decompiler_tools():
        attempt = {'tool': name}
        with tempfile.TemporaryDirectory(prefix='ts4-decompile-') as temp:
            candidate = Path(temp) / (Path(src_file).stem + '.py')
            try:
                rv = run([executable, '-o', temp, src_file], text=True,
                         encoding='utf-8', errors='replace', capture_output=True,
                         timeout=timeout)
                attempt.update(returncode=rv.returncode, stdout=rv.stdout, stderr=rv.stderr)
                error = validate_source(candidate)
                if rv.returncode != 0:
                    error = error or 'Decompiler exited with code {}'.format(rv.returncode)
            except (OSError, TimeoutExpired) as exc:
                error = '{}: {}'.format(type(exc).__name__, exc)
            attempt['error'] = error
            result['attempts'].append(attempt)
            if error is None:
                Path(dest_path).mkdir(parents=True, exist_ok=True)
                shutil.copy2(str(candidate), str(Path(dest_path) / candidate.name))
                result.update(validated=True, tool=name)
                break
            diagnostics.mkdir(parents=True, exist_ok=True)
            if candidate.exists():
                shutil.copy2(str(candidate), str(diagnostics / (name + '.py')))
    if not result['validated']:
        diagnostics.mkdir(parents=True, exist_ok=True)
    if diagnostics.exists():
        (diagnostics / 'attempts.json').write_text(
            json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    return result


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
    success = sum(1 for x in rv if x['validated'])

    elapsed = time.time() - start
    print("Finished decompilation under folder %s after %d secs." % (
        src, elapsed))
    rate = success * 100.0 / total if total else 100.0
    print('Syntax-validated: {}/{} ({:.2f}%)'.format(success, total, rate))
    return rv


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
    if sys.version_info[:2] != (3, 7):
        raise RuntimeError('Run this Sims 4 validation pipeline with Python 3.7')
    if len(decompiler_tools()) == 1:
        print('Optional decompyle3 fallback unavailable. Install with: python -m pip install decompyle3')
    results = []
    for folder in [
        os.path.join(project_game_unzip_dir, x) for x in os.listdir(
            project_game_unzip_dir)]:
        if os.path.isdir(folder):
            results.extend(decompile(folder))
    report = Path(project_dir) / 'game' / 'decompile-report.json'
    total = len(results)
    success = sum(1 for item in results if item['validated'])
    report.write_text(json.dumps({
        'validation': 'Python 3.7 compile only; semantic equivalence not verified',
        'total': total, 'validated': success, 'failed': total - success,
        'files': results,
    }, ensure_ascii=False, indent=2), encoding='utf-8')
    print('Report: {}'.format(report))
    if not total:
        sys.exit('No .pyc files found; src was not updated.')
    if success * 100.0 / total < success_rate:
        sys.exit('Validated success rate is lower than {}%; src was not updated.'.format(success_rate))

def copy_folders_to_src():
    backup = Path(tempfile.mkdtemp(prefix='src-backup-', dir=os.path.join(project_dir, 'game')))
    # The library folders that need to be copied for writing convenience.
    folders = [os.path.join("base", "lib"), "core", "simulation"]
    for folder in folders:
        src_folder = os.path.join(project_game_decompile_dir, folder)
        if folder == folders[0]:
            target_folder = os.path.join(project_src_dir, "lib")
        else:
            target_folder = os.path.join(project_src_dir, folder)
        for source in Path(src_folder).rglob('*.py'):
            if validate_source(source) is not None:
                continue
            relative = source.relative_to(src_folder)
            target = Path(target_folder) / relative
            if target.exists():
                saved = backup / Path(target_folder).name / relative
                saved.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(str(target), str(saved))
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(source), str(target))
    print('Previous src files backed up to: {}'.format(backup))
    print('Files without validated replacements were retained and may be stale; consult the report.')

def prepare():
    create_directory(os.path.join(project_dir, 'game'))
    copy_files_and_unzip()
    prepare_directory(project_game_decompile_dir)


if __name__ == '__main__':
    multiprocessing.freeze_support()
    if sys.version_info[:2] != (3, 7):
        sys.exit('Please run decompile.py with Python 3.7.')
    prepare()
    run_decompile()
    copy_folders_to_src()
