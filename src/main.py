"""Инструмент визуализации графа зависимостей пакетов Cargo (Rust)."""

import argparse
import sys

from cargo import CargoRegistry, RegistryError
from config import ConfigError, load_config
from graph import build_graph, find_cycles
from local_repo import FileRepository
from visual import ascii_tree, dot_source, save_svg

DEFAULT_CONFIG = "config.xml"


def parse_args(argv=None):
    """Разбирает командную строку: путь к XML-файлу конфигурации."""
    parser = argparse.ArgumentParser(
        description="Визуализатор графа зависимостей пакетов Cargo")
    parser.add_argument(
        "config", nargs="?", default=DEFAULT_CONFIG,
        help=f"путь к конфигурационному XML (по умолчанию {DEFAULT_CONFIG})")
    return parser.parse_args(argv)


def print_problems(title, problems):
    """Печатает заголовок и список ошибок в поток ошибок."""
    print(title, file=sys.stderr)
    for problem in problems:
        print(f"  - {problem}", file=sys.stderr)


def open_repository(config):
    """Создаёт тестовый репозиторий из файла или реестр Cargo по URL."""
    if config.test_mode:
        return FileRepository(config.repository)
    return CargoRegistry(config.repository)


def analyze(config):
    """Строит граф зависимостей пакета по параметрам конфигурации."""
    repository = open_repository(config)
    repository.check_package(config.package)
    return build_graph(config.package, repository.dependencies,
                       config.max_depth, config.filter_text)


def print_cycles(cycles):
    """Печатает найденные циклические зависимости."""
    if not cycles:
        print("Циклические зависимости: не найдены")
        return
    print("Циклические зависимости:")
    for cycle in cycles:
        print("  " + " -> ".join(cycle))


def visualize(config, graph, cycles):
    """Выводит ASCII-дерево и описание DOT, сохраняет изображение SVG."""
    if config.ascii_tree:
        print(f"Зависимости пакета {graph.root} (ASCII-дерево):")
        print(ascii_tree(graph))
        print()
    print("Граф на языке Graphviz (DOT):")
    print(dot_source(graph, cycles))
    print()
    method = save_svg(graph, cycles, config.output_file)
    print(f"Изображение графа сохранено в {config.output_file} ({method})")


def main(argv=None):
    """Строит граф зависимостей пакета и визуализирует его."""
    args = parse_args(argv)
    try:
        config = load_config(args.config)
    except ConfigError as error:
        print_problems("Ошибка конфигурации:", error.problems)
        return 1
    try:
        graph = analyze(config)
    except RegistryError as error:
        print_problems("Ошибка получения зависимостей:", [str(error)])
        return 1
    cycles = find_cycles(graph.edges, graph.root)
    try:
        visualize(config, graph, cycles)
    except OSError as error:
        print_problems("Ошибка сохранения изображения:", [str(error)])
        return 1
    print_cycles(cycles)
    return 0


if __name__ == "__main__":
    sys.exit(main())
