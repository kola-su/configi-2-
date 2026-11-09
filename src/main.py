"""Инструмент визуализации графа зависимостей пакетов Cargo (Rust)."""

import argparse
import sys

from cargo import CargoRegistry, RegistryError
from config import ConfigError, load_config
from graph import build_graph, find_cycles, load_order
from local_repo import FileRepository

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


def describe_package(graph, name):
    """Возвращает строку вида 'A -> B, C' для одного пакета."""
    if not graph.is_expanded(name):
        return f"{name} -> не анализировался: достигнута максимальная " \
               f"глубина"
    deps = graph.edges[name]
    return f"{name} -> {', '.join(deps) if deps else 'нет зависимостей'}"


def print_graph(graph):
    """Печатает граф: зависимости каждого пакета в порядке BFS."""
    print(f"Граф зависимостей пакета {graph.root}")
    print(f"Максимальная глубина: {graph.max_depth}")
    for name in graph.packages():
        print(describe_package(graph, name))
    if graph.skipped:
        print(f"Исключены фильтром: {', '.join(sorted(graph.skipped))}")
    print(f"Пакетов в графе: {len(graph.levels)}")


def print_cycles(cycles):
    """Печатает найденные циклические зависимости."""
    if not cycles:
        print("Циклические зависимости: не найдены")
        return
    print("Циклические зависимости:")
    for cycle in cycles:
        print("  " + " -> ".join(cycle))


def print_load_order(graph, cycles):
    """Печатает порядок загрузки зависимостей пакета."""
    print(f"Порядок загрузки зависимостей пакета {graph.root}:")
    for number, name in enumerate(load_order(graph.edges, graph.root), 1):
        print(f"  {number}. {name}")
    if cycles:
        print("Порядок неполный: из-за циклов пропущены рёбра "
              + ", ".join(f"{cycle[-2]} -> {cycle[-1]}" for cycle in cycles))


def main(argv=None):
    """Строит граф зависимостей и выводит его и порядок загрузки."""
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
    print_graph(graph)
    print_cycles(cycles)
    print()
    print_load_order(graph, cycles)
    return 0


if __name__ == "__main__":
    sys.exit(main())
