"""Тесты получения прямых зависимостей пакетов Cargo по URL."""

import contextlib
import functools
import http.server
import importlib
import io
import json
import sys
import tempfile
import threading
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

cargo = importlib.import_module("cargo")
main = importlib.import_module("main")


def version(vers, deps=(), yanked=False):
    """Строит JSON-описание версии пакета как в индексе crates.io."""
    return {"name": "demo", "vers": vers, "deps": list(deps),
            "yanked": yanked}


def dep(name, kind="normal", optional=False, package=None):
    """Строит описание зависимости как в индексе crates.io."""
    data = {"name": name, "req": "^1", "kind": kind, "optional": optional}
    if package:
        data["package"] = package
    return data


def index_text(*versions):
    """Склеивает версии в текст файла индекса: по строке на версию."""
    return "\n".join(json.dumps(entry) for entry in versions) + "\n"


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    """Раздаёт файлы каталога без вывода журнала запросов."""

    def log_message(self, *args):
        """Не печатает журнал запросов во время тестов."""


@contextlib.contextmanager
def serve(folder):
    """Запускает локальный HTTP-сервер индекса и возвращает его URL."""
    handler = functools.partial(QuietHandler, directory=folder)
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}"
    finally:
        server.shutdown()
        server.server_close()


def write_index(folder, name, text):
    """Кладёт файл пакета в каталог по правилам индекса Cargo."""
    path = Path(folder) / cargo.index_path(name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


class IndexPathTest(unittest.TestCase):
    """Проверяет пути к файлам пакетов в индексе."""

    def test_paths(self):
        """Короткие и длинные имена, регистр букв."""
        self.assertEqual(cargo.index_path("a"), "1/a")
        self.assertEqual(cargo.index_path("ab"), "2/ab")
        self.assertEqual(cargo.index_path("syn"), "3/s/syn")
        self.assertEqual(cargo.index_path("Serde"), "se/rd/serde")
        self.assertEqual(cargo.index_path("serde_json"), "se/rd/serde_json")


class ParseTest(unittest.TestCase):
    """Проверяет разбор индекса и выбор версии."""

    def test_parse_and_bad_line(self):
        """Пустые строки пропускаются, битый JSON — ошибка."""
        text = index_text(version("1.0.0")) + "\n"
        self.assertEqual(len(cargo.parse_index(text)), 1)
        with self.assertRaises(cargo.RegistryError):
            cargo.parse_index("{bad json")

    def test_latest_version(self):
        """1.10 новее 1.9, yanked и pre-release не выбираются."""
        versions = [version("1.9.0"), version("1.10.0"),
                    version("2.0.0", yanked=True),
                    version("1.11.0-beta.1")]
        self.assertEqual(cargo.latest_version(versions)["vers"], "1.10.0")

    def test_only_prerelease(self):
        """Если стабильных версий нет, берётся pre-release."""
        versions = [version("0.1.0-alpha"), version("0.2.0-alpha")]
        self.assertEqual(cargo.latest_version(versions)["vers"],
                         "0.2.0-alpha")

    def test_no_versions(self):
        """Все версии отозваны — ошибка."""
        with self.assertRaises(cargo.RegistryError):
            cargo.latest_version([version("1.0.0", yanked=True)])

    def test_direct_dependencies(self):
        """Учитываются только обычные обязательные зависимости."""
        entry = version("1.0.0", [
            dep("serde"), dep("syn", kind=None),
            dep("tempfile", kind="dev"), dep("cc", kind="build"),
            dep("indexmap", optional=True),
            dep("alias", package="memchr"), dep("serde")])
        names = [name for name, _req in cargo.direct_dependencies(entry)]
        self.assertEqual(names, ["memchr", "serde", "syn"])


class RegistryTest(unittest.TestCase):
    """Проверяет загрузку данных по URL."""

    def test_fake_fetch_and_cache(self):
        """URL строится по индексу, повторный запрос берётся из кэша."""
        calls = []

        def fake_fetch(url):
            """Запоминает URL и возвращает готовый индекс."""
            calls.append(url)
            return index_text(version("1.0.0", [dep("itoa")]))

        registry = cargo.CargoRegistry("https://example.org/", fake_fetch)
        self.assertEqual(registry.dependencies("serde_json"), ["itoa"])
        self.assertEqual(registry.dependencies("serde_json"), ["itoa"])
        self.assertEqual(calls, ["https://example.org/se/rd/serde_json"])

    def test_http_server(self):
        """Реальный HTTP-запрос к локальному серверу и ошибка 404."""
        with tempfile.TemporaryDirectory() as folder:
            write_index(folder, "demo", index_text(
                version("0.1.0", [dep("ryu")]),
                version("0.2.0", [dep("itoa"), dep("ryu")])))
            with serve(folder) as url:
                registry = cargo.CargoRegistry(url)
                self.assertEqual(registry.dependencies("demo"),
                                 ["itoa", "ryu"])
                with self.assertRaises(cargo.RegistryError) as caught:
                    registry.dependencies("missing")
        self.assertIn("не найден", str(caught.exception))

    def test_unreachable(self):
        """Недоступный адрес — понятная ошибка, а не падение."""
        with self.assertRaises(cargo.RegistryError):
            cargo.fetch_text("http://127.0.0.1:9/nothing")


class MainTest(unittest.TestCase):
    """Проверяет граф реального формата Cargo через HTTP."""

    def test_transitive_graph(self):
        """Транзитивные зависимости загружаются по URL репозитория."""
        with tempfile.TemporaryDirectory() as folder:
            write_index(folder, "demo", index_text(
                version("1.2.3", [dep("serde"), dep("itoa")])))
            write_index(folder, "serde", index_text(
                version("1.0.0", [dep("serde_derive", optional=True)])))
            write_index(folder, "itoa", index_text(version("1.0.0")))
            with serve(folder) as url:
                config = ROOT / "config.xml"
                text = config.read_text(encoding="utf-8")
                text = text.replace("https://index.crates.io", url)
                text = text.replace("serde_json<", "demo<")
                path = Path(folder) / "config.xml"
                path.write_text(text, encoding="utf-8")
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    code = main.main([str(path)])
        self.assertEqual(code, 0)
        lines = output.getvalue().splitlines()
        self.assertIn("demo -> itoa, serde", lines)
        self.assertIn("serde -> нет зависимостей", lines)
        self.assertIn("Пакетов в графе: 3", lines)
