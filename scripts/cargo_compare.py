"""Сравнение с настоящим менеджером пакетов Cargo на тестовом графе.

Скрипт превращает файл тестового репозитория в рабочее пространство
(workspace) Cargo: каждый пакет — отдельный крейт с зависимостями через
path. Затем запускается настоящий Cargo без доступа к сети, и его
порядок сборки сравнивается с порядком загрузки, который вычисляет
визуализатор.

Запуск: python scripts/cargo_compare.py examples/simple.txt A
"""

import argparse
import importlib
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

graph_module = importlib.import_module("graph")
local_repo = importlib.import_module("local_repo")

DEFAULT_OUT = ROOT / "build" / "cargo"
COMPILING = re.compile(r"Compiling (\S+) v")


def crate_name(package):
    """Имя крейта Cargo для пакета тестового репозитория."""
    return package.lower()


def crate_manifest(package, deps):
    """Текст Cargo.toml для одного пакета с зависимостями через path."""
    lines = ["[package]", f'name = "{crate_name(package)}"',
             'version = "0.1.0"', 'edition = "2021"', "",
             "[dependencies]"]
    for dep in deps:
        lines.append(f'{crate_name(dep)} = {{ path = "../{crate_name(dep)}" }}')
    return "\n".join(lines) + "\n"


def write_workspace(graph, folder):
    """Создаёт workspace Cargo по словарю пакет -> зависимости."""
    packages = sorted(set(graph) | {d for deps in graph.values() for d in deps})
    members = ", ".join(f'"{crate_name(name)}"' for name in packages)
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "Cargo.toml").write_text(
        f'[workspace]\nmembers = [{members}]\nresolver = "2"\n',
        encoding="utf-8")
    for name in packages:
        crate = folder / crate_name(name)
        (crate / "src").mkdir(parents=True, exist_ok=True)
        (crate / "Cargo.toml").write_text(
            crate_manifest(name, graph.get(name, [])), encoding="utf-8")
        (crate / "src" / "lib.rs").write_text(
            f"//! Тестовый пакет {name}.\n", encoding="utf-8")


def run_cargo(folder, *args):
    """Запускает Cargo в каталоге workspace без доступа к сети."""
    return subprocess.run(["cargo", *args, "--offline"], cwd=folder,
                          capture_output=True, text=True, check=False)


def cargo_build_order(folder, package):
    """Возвращает порядок сборки Cargo (-j 1) или текст ошибки."""
    run_cargo(folder, "clean")
    result = run_cargo(folder, "build", "-j", "1", "-p", crate_name(package))
    if result.returncode:
        return None, result.stderr.strip().splitlines()[0]
    order = COMPILING.findall(result.stderr)
    return [name.upper() for name in order], ""


def parse_args(argv=None):
    """Разбирает аргументы: файл тестового графа и имя пакета."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("graph_file", help="файл тестового репозитория")
    parser.add_argument("package", help="анализируемый пакет")
    parser.add_argument("--out", default=None, help="каталог для workspace")
    return parser.parse_args(argv)


def main(argv=None):
    """Печатает порядок визуализатора и порядок сборки Cargo рядом."""
    args = parse_args(argv)
    repository = local_repo.FileRepository(args.graph_file)
    graph = graph_module.build_graph(args.package, repository.dependencies,
                                     len(repository.graph) + 1)
    ours = graph_module.load_order(graph.edges, args.package)
    folder = Path(args.out) if args.out else DEFAULT_OUT / Path(
        args.graph_file).stem
    write_workspace(repository.graph, folder)
    cargo, error = cargo_build_order(folder, args.package)
    print(f"Визуализатор: {' '.join(ours)}")
    if cargo is None:
        print(f"Cargo: ошибка\n{error}")
        return 1
    print(f"Cargo:        {' '.join(cargo)}")
    print("Совпадает" if cargo == ours else "Отличается")
    return 0


if __name__ == "__main__":
    sys.exit(main())
