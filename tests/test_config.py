"""Тесты чтения и проверки XML-конфигурации."""

import contextlib
import importlib
import io
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

config = importlib.import_module("config")
main = importlib.import_module("main")

DEFAULTS = {
    "package": "serde_json",
    "repository": "https://index.crates.io",
    "test_mode": "false",
    "output_file": "graph.svg",
    "ascii_tree": "true",
    "max_depth": "2",
    "filter": "",
}


def make_xml(**changes):
    """Строит текст XML из значений по умолчанию и изменений.

    Значение None убирает параметр из файла.
    """
    values = dict(DEFAULTS, **changes)
    tags = [f"<{key}>{value}</{key}>"
            for key, value in values.items() if value is not None]
    return "<config>" + "".join(tags) + "</config>"


def load_text(text):
    """Записывает XML во временный файл и загружает конфигурацию."""
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "config.xml"
        path.write_text(text, encoding="utf-8")
        return config.load_config(str(path))


def problems_of(text):
    """Возвращает список ошибок для XML, который не должен загрузиться."""
    try:
        load_text(text)
    except config.ConfigError as error:
        return error.problems
    raise AssertionError("ожидалась ошибка конфигурации")


class LoadTest(unittest.TestCase):
    """Проверяет загрузку корректной конфигурации."""

    def test_defaults(self):
        """Все параметры читаются и приводятся к нужным типам."""
        result = load_text(make_xml(filter="derive"))
        self.assertEqual(result.package, "serde_json")
        self.assertFalse(result.test_mode)
        self.assertTrue(result.ascii_tree)
        self.assertEqual(result.max_depth, 2)
        self.assertEqual(result.filter_text, "derive")

    def test_filter_optional(self):
        """Фильтр можно не указывать: тогда он пустой."""
        result = load_text(make_xml(filter=None))
        self.assertEqual(result.filter_text, "")

    def test_items_order(self):
        """Пары ключ-значение идут в порядке тегов XML."""
        keys = [key for key, _value in load_text(make_xml()).items()]
        self.assertEqual(keys, list(config.FIELDS))

    def test_test_mode(self):
        """В тестовом режиме repository — существующий файл."""
        with tempfile.NamedTemporaryFile(suffix=".txt") as graph:
            text = make_xml(package="A", repository=graph.name,
                            test_mode="yes")
            result = load_text(text)
        self.assertTrue(result.test_mode)
        self.assertEqual(result.package, "A")


class ErrorTest(unittest.TestCase):
    """Проверяет обработку ошибок для каждого параметра."""

    def test_file_errors(self):
        """Нет файла, битый XML и неверный корневой тег."""
        with self.assertRaises(config.ConfigError):
            config.load_config(str(ROOT / "no_such.xml"))
        self.assertIn("некорректный XML", problems_of("<config>")[0])
        self.assertIn("корневой тег", problems_of("<a></a>")[0])

    def test_missing_and_empty(self):
        """Отсутствующий и пустой обязательный параметр."""
        self.assertIn("отсутствует", problems_of(make_xml(package=None))[0])
        self.assertIn("пустым", problems_of(make_xml(output_file=""))[0])

    def test_unknown_and_duplicate(self):
        """Неизвестный тег и повтор тега."""
        text = make_xml().replace("</config>", "<x>1</x><filter/></config>")
        problems = problems_of(text)
        self.assertIn("неизвестный параметр <x>", problems)
        self.assertIn("параметр <filter> задан дважды", problems)

    def test_values(self):
        """Неверные значения каждого параметра."""
        cases = {
            "package": "bad name",
            "repository": "index.crates.io",
            "test_mode": "maybe",
            "output_file": "graph.png",
            "ascii_tree": "tree",
            "max_depth": "0",
            "filter": "a b",
        }
        for key, value in cases.items():
            with self.subTest(key=key):
                problems = problems_of(make_xml(**{key: value}))
                self.assertTrue(problems[0].startswith(f"<{key}>"))

    def test_depth_not_number(self):
        """Глубина должна быть целым числом."""
        problems = problems_of(make_xml(max_depth="two"))
        self.assertIn("целое число", problems[0])

    def test_test_mode_errors(self):
        """В тестовом режиме: строчные буквы и отсутствующий файл."""
        text = make_xml(package="abc", repository="missing.txt",
                        test_mode="true")
        self.assertEqual(len(problems_of(text)), 2)

    def test_all_errors_at_once(self):
        """Ошибки всех параметров выводятся вместе."""
        text = make_xml(package="?", repository="ftp://x", max_depth="-1",
                        output_file="a.jpg", ascii_tree="x", filter="*")
        self.assertEqual(len(problems_of(text)), 6)


class MainTest(unittest.TestCase):
    """Проверяет вывод программы."""

    def test_prints_key_value(self):
        """Корректный config.xml выводится парами ключ=значение."""
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = main.main([str(ROOT / "config.xml")])
        self.assertEqual(code, 0)
        self.assertIn("package=serde_json", output.getvalue())
        self.assertIn("max_depth=2", output.getvalue())

    def test_error_exit_code(self):
        """При ошибке конфигурации код возврата 1 и текст в stderr."""
        errors = io.StringIO()
        with contextlib.redirect_stderr(errors):
            code = main.main([str(ROOT / "configs/errors/all_errors.xml")])
        self.assertEqual(code, 1)
        self.assertIn("Ошибка конфигурации", errors.getvalue())


if __name__ == "__main__":
    unittest.main()
