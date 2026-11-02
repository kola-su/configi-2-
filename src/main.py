"""Инструмент визуализации графа зависимостей пакетов Cargo (Rust)."""

import argparse
import sys

from cargo import CargoRegistry, RegistryError, direct_dependencies
from config import ConfigError, load_config

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


def print_direct(registry, package):
    """Печатает прямые зависимости новейшей версии пакета."""
    entry = registry.latest(package)
    deps = direct_dependencies(entry)
    print(f"Пакет: {entry['name']} {entry['vers']}")
    if not deps:
        print("Прямых зависимостей нет")
        return
    print(f"Прямые зависимости ({len(deps)}):")
    for name, requirement in deps:
        print(f"  {name} {requirement}")


def main(argv=None):
    """Загружает конфигурацию и выводит прямые зависимости пакета."""
    args = parse_args(argv)
    try:
        config = load_config(args.config)
    except ConfigError as error:
        print_problems("Ошибка конфигурации:", error.problems)
        return 1
    if config.test_mode:
        print_problems("Ошибка:", ["режим тестового репозитория "
                                   "пока не поддерживается"])
        return 1
    try:
        print_direct(CargoRegistry(config.repository), config.package)
    except RegistryError as error:
        print_problems("Ошибка получения зависимостей:", [str(error)])
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
