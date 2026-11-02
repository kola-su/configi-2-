"""Получение зависимостей пакетов Cargo из индекса реестра по URL.

Используется разреженный (sparse) формат индекса crates.io: для каждого
пакета по адресу <URL>/<путь> лежит текстовый файл, где каждая строка —
JSON-описание одной версии пакета со списком её зависимостей.
"""

import json
import urllib.error
import urllib.request

TIMEOUT_SECONDS = 20
USER_AGENT = "dependency-visualizer (study project)"
NOT_FOUND_CODES = (404, 410, 451)
ONE_LETTER = 1
TWO_LETTERS = 2
THREE_LETTERS = 3
PREFIX_SIZE = 2
NORMAL_KINDS = (None, "normal")


class RegistryError(Exception):
    """Ошибка получения или разбора данных репозитория."""


def index_path(name):
    """Возвращает путь к файлу пакета в индексе по правилам Cargo.

    1 и 2 символа: 1/a, 2/ab; 3 символа: 3/a/abc;
    иначе: первые две буквы / следующие две / имя (se/rd/serde).
    """
    name = name.lower()
    size = len(name)
    if size in (ONE_LETTER, TWO_LETTERS):
        return f"{size}/{name}"
    if size == THREE_LETTERS:
        return f"{size}/{name[0]}/{name}"
    first = name[:PREFIX_SIZE]
    second = name[PREFIX_SIZE:PREFIX_SIZE * 2]
    return f"{first}/{second}/{name}"


def fetch_text(url):
    """Скачивает текст по URL средствами стандартной библиотеки."""
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as page:
            return page.read().decode("utf-8")
    except urllib.error.HTTPError as error:
        if error.code in NOT_FOUND_CODES:
            raise RegistryError(f"пакет не найден в репозитории: {url}") \
                from error
        raise RegistryError(f"ошибка HTTP {error.code}: {url}") from error
    except (urllib.error.URLError, OSError) as error:
        reason = getattr(error, "reason", error)
        raise RegistryError(f"нет доступа к {url}: {reason}") from error


def parse_index(text):
    """Разбирает файл индекса: одна строка — одна версия пакета."""
    versions = []
    for number, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            versions.append(json.loads(line))
        except json.JSONDecodeError as error:
            raise RegistryError(f"некорректная строка индекса "
                                f"{number}: {error}") from error
    return versions


def version_key(version):
    """Ключ сравнения версий semver: числа, затем релиз выше pre-release."""
    core, _plus, _build = version.partition("+")
    numbers, dash, _pre = core.partition("-")
    parts = tuple(int(part) if part.isdigit() else 0
                  for part in numbers.split("."))
    return parts, not dash


def latest_version(versions):
    """Выбирает новейшую неотозванную версию, по возможности не pre-release.

    Отозванные (yanked) версии не учитываются.
    """
    alive = [entry for entry in versions if not entry.get("yanked")]
    stable = [entry for entry in alive if "-" not in entry["vers"]]
    candidates = stable or alive
    if not candidates:
        raise RegistryError("у пакета нет доступных версий")
    return max(candidates, key=lambda entry: version_key(entry["vers"]))


def direct_dependencies(entry):
    """Возвращает прямые зависимости версии: список пар (имя, требование).

    Учитываются обычные (normal) обязательные зависимости; dev-, build-
    и необязательные (optional) зависимости пропускаются. Для
    переименованных зависимостей берётся настоящее имя пакета.
    """
    found = {}
    for dep in entry.get("deps", []):
        if dep.get("kind") not in NORMAL_KINDS or dep.get("optional"):
            continue
        name = dep.get("package") or dep["name"]
        found.setdefault(name, dep.get("req", "*"))
    return sorted(found.items())


class CargoRegistry:
    """Репозиторий пакетов Cargo, доступный по URL индекса."""

    def __init__(self, base_url, fetch=fetch_text):
        """Запоминает адрес индекса и функцию загрузки текста."""
        self.base_url = base_url.rstrip("/")
        self.fetch = fetch
        self.cache = {}

    def package_url(self, name):
        """Возвращает URL файла индекса для пакета."""
        return f"{self.base_url}/{index_path(name)}"

    def latest(self, name):
        """Возвращает описание новейшей версии пакета (с кэшем)."""
        if name not in self.cache:
            text = self.fetch(self.package_url(name))
            self.cache[name] = latest_version(parse_index(text))
        return self.cache[name]

    def dependencies(self, name):
        """Возвращает имена прямых зависимостей новейшей версии пакета."""
        return [dep for dep, _req in direct_dependencies(self.latest(name))]
