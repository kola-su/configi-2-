"""Тестовый репозиторий: описание графа пакетов в текстовом файле.

Формат файла — по строке на пакет:

    A: B C
    B: D
    D:

Слева от двоеточия имя пакета, справа — его прямые зависимости через
пробел. Имена пакетов — большие латинские буквы. Пустые строки и
строки, начинающиеся с '#', пропускаются.
"""

import re

from cargo import RegistryError

LINE = re.compile(r"([A-Z]+)\s*:\s*((?:[A-Z]+\s*)*)")
COMMENT_SIGN = "#"


def parse_graph(text):
    """Разбирает описание графа в словарь пакет -> список зависимостей."""
    graph = {}
    for number, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith(COMMENT_SIGN):
            continue
        match = LINE.fullmatch(line)
        if not match:
            raise RegistryError(f"строка {number}: ожидается 'ПАКЕТ: "
                                f"ЗАВИСИМОСТИ' из больших латинских "
                                f"букв, получено '{line}'")
        name, deps = match.group(1), match.group(2).split()
        if name in graph:
            raise RegistryError(f"строка {number}: пакет {name} "
                                f"описан повторно")
        graph[name] = list(dict.fromkeys(deps))
    return graph


class FileRepository:
    """Репозиторий пакетов, прочитанный из файла описания графа."""

    def __init__(self, path):
        """Читает и разбирает файл тестового репозитория."""
        try:
            with open(path, encoding="utf-8") as source:
                self.graph = parse_graph(source.read())
        except OSError as error:
            raise RegistryError(f"не удалось прочитать файл "
                                f"{path}: {error}") from error

    def check_package(self, name):
        """Проверяет, что анализируемый пакет описан в репозитории."""
        if name not in self.graph:
            raise RegistryError(f"пакет {name} не найден в тестовом "
                                f"репозитории")

    def dependencies(self, name):
        """Возвращает прямые зависимости пакета.

        Пакет, который упоминается только как зависимость, считается
        пакетом без зависимостей.
        """
        return list(self.graph.get(name, []))
