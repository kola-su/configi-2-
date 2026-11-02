"""Инструмент визуализации графа зависимостей пакетов Cargo (Rust)."""

import argparse
import sys

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


def print_config(config):
    """Печатает все параметры пользователя в формате ключ=значение."""
    for key, value in config.items():
        print(f"{key}={value}")


def main(argv=None):
    """Загружает конфигурацию и выводит её параметры."""
    args = parse_args(argv)
    try:
        config = load_config(args.config)
    except ConfigError as error:
        print_problems("Ошибка конфигурации:", error.problems)
        return 1
    print_config(config)
    return 0


if __name__ == "__main__":
    sys.exit(main())
