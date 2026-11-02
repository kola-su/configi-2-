"""Чтение и проверка конфигурационного файла формата XML."""

import os
import re
import xml.etree.ElementTree as xml_tree
from dataclasses import dataclass

ROOT_TAG = "config"
MIN_DEPTH = 1
TRUE_WORDS = ("true", "yes", "1")
FALSE_WORDS = ("false", "no", "0")
SVG_SUFFIX = ".svg"
URL_PREFIXES = ("http://", "https://")
CRATE_NAME = re.compile(r"[A-Za-z][A-Za-z0-9_-]{0,63}")
TEST_NAME = re.compile(r"[A-Z]+")
FILTER_TEXT = re.compile(r"[A-Za-z0-9_-]*")
FIELDS = (
    "package",
    "repository",
    "test_mode",
    "output_file",
    "ascii_tree",
    "max_depth",
    "filter",
)


class ConfigError(Exception):
    """Ошибка конфигурации со списком всех найденных проблем."""

    def __init__(self, problems):
        """Сохраняет список сообщений об ошибках."""
        super().__init__("\n".join(problems))
        self.problems = problems


@dataclass
class Config:
    """Параметры, которые задаёт пользователь."""

    package: str
    repository: str
    test_mode: bool
    output_file: str
    ascii_tree: bool
    max_depth: int
    filter_text: str

    def items(self):
        """Возвращает пары (ключ, значение) в порядке тегов XML."""
        values = (
            self.package,
            self.repository,
            format_bool(self.test_mode),
            self.output_file,
            format_bool(self.ascii_tree),
            str(self.max_depth),
            self.filter_text,
        )
        return list(zip(FIELDS, values))


def format_bool(value):
    """Записывает логическое значение так же, как в XML."""
    return "true" if value else "false"


def read_xml(path):
    """Читает XML и возвращает словарь тег -> текст.

    Проверяет наличие файла, корректность XML, корневой тег,
    неизвестные и повторяющиеся параметры.
    """
    if not os.path.isfile(path):
        raise ConfigError([f"файл конфигурации не найден: {path}"])
    try:
        root = xml_tree.parse(path).getroot()
    except xml_tree.ParseError as error:
        raise ConfigError([f"некорректный XML: {error}"]) from error
    if root.tag != ROOT_TAG:
        raise ConfigError([f"корневой тег должен быть <{ROOT_TAG}>"])
    values = {}
    problems = []
    for child in root:
        if child.tag not in FIELDS:
            problems.append(f"неизвестный параметр <{child.tag}>")
        elif child.tag in values:
            problems.append(f"параметр <{child.tag}> задан дважды")
        else:
            values[child.tag] = (child.text or "").strip()
    if problems:
        raise ConfigError(problems)
    return values


def require(values, name, problems):
    """Возвращает обязательное значение или запоминает ошибку."""
    if name not in values:
        problems.append(f"отсутствует параметр <{name}>")
        return None
    if not values[name]:
        problems.append(f"параметр <{name}> не должен быть пустым")
        return None
    return values[name]


def parse_bool(values, name, problems):
    """Разбирает логический параметр: true/false, yes/no, 1/0."""
    text = require(values, name, problems)
    if text is None:
        return None
    if text.lower() in TRUE_WORDS:
        return True
    if text.lower() in FALSE_WORDS:
        return False
    problems.append(f"<{name}>: ожидается true или false, получено '{text}'")
    return None


def parse_depth(values, problems):
    """Разбирает максимальную глубину анализа: целое число от 1."""
    text = require(values, "max_depth", problems)
    if text is None:
        return None
    try:
        depth = int(text)
    except ValueError:
        problems.append(f"<max_depth>: ожидается целое число, "
                        f"получено '{text}'")
        return None
    if depth < MIN_DEPTH:
        problems.append(f"<max_depth>: глубина должна быть не меньше "
                        f"{MIN_DEPTH}, получено {depth}")
        return None
    return depth


def check_package(values, test_mode, problems):
    """Проверяет имя пакета по правилам Cargo или тестового режима."""
    name = require(values, "package", problems)
    if name is None:
        return None
    if test_mode and not TEST_NAME.fullmatch(name):
        problems.append(f"<package>: в тестовом режиме имя пакета — "
                        f"большие латинские буквы, получено '{name}'")
        return None
    if not test_mode and not CRATE_NAME.fullmatch(name):
        problems.append(f"<package>: недопустимое имя пакета Cargo "
                        f"'{name}'")
        return None
    return name


def check_repository(values, test_mode, problems):
    """Проверяет URL репозитория или путь к файлу тестового графа."""
    place = require(values, "repository", problems)
    if place is None:
        return None
    if test_mode and not os.path.isfile(place):
        problems.append(f"<repository>: файл тестового репозитория "
                        f"не найден: {place}")
        return None
    if not test_mode and not place.startswith(URL_PREFIXES):
        problems.append(f"<repository>: URL должен начинаться с http:// "
                        f"или https://, получено '{place}'")
        return None
    return place


def check_output(values, problems):
    """Проверяет имя файла изображения графа: нужно расширение .svg."""
    name = require(values, "output_file", problems)
    if name is None:
        return None
    if not name.lower().endswith(SVG_SUFFIX) or name == SVG_SUFFIX:
        problems.append(f"<output_file>: имя файла должно оканчиваться "
                        f"на {SVG_SUFFIX}, получено '{name}'")
        return None
    return name


def check_filter(values, problems):
    """Проверяет подстроку фильтра: пустая или символы имён пакетов."""
    text = values.get("filter", "")
    if not FILTER_TEXT.fullmatch(text):
        problems.append(f"<filter>: подстрока может содержать только "
                        f"латинские буквы, цифры, '_' и '-', "
                        f"получено '{text}'")
        return None
    return text


def load_config(path):
    """Загружает конфигурацию и проверяет все параметры сразу.

    Если найдены ошибки, выбрасывает ConfigError со всеми сообщениями.
    """
    values = read_xml(path)
    problems = []
    test_mode = parse_bool(values, "test_mode", problems)
    config = Config(
        package=check_package(values, test_mode, problems),
        repository=check_repository(values, test_mode, problems),
        test_mode=test_mode,
        output_file=check_output(values, problems),
        ascii_tree=parse_bool(values, "ascii_tree", problems),
        max_depth=parse_depth(values, problems),
        filter_text=check_filter(values, problems),
    )
    if problems:
        raise ConfigError(problems)
    return config
