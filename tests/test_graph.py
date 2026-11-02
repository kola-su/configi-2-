"""Тесты построения графа (BFS), глубины, фильтра и циклов."""

import contextlib
import importlib
import io
import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

graph_module = importlib.import_module("graph")
local_repo = importlib.import_module("local_repo")
main = importlib.import_module("main")
cargo = importlib.import_module("cargo")

SIMPLE = {"A": ["B", "C"], "B": ["D", "E"], "C": ["E", "F"], "E": ["G"]}
CYCLE = {"A": ["B"], "B": ["C"], "C": ["A", "D"], "D": ["D"]}


def getter(edges):
    """Возвращает функцию прямых зависимостей для словаря-графа."""
    return lambda name: edges.get(name, [])


def build(edges, root="A", depth=10, filter_text=""):
    """Строит граф по словарю с заданными глубиной и фильтром."""
    return graph_module.build_graph(root, getter(edges), depth, filter_text)


def run_main(config_path):
    """Запускает программу и возвращает (код, stdout, stderr)."""
    output, errors = io.StringIO(), io.StringIO()
    previous = os.getcwd()
    os.chdir(ROOT)
    try:
        with contextlib.redirect_stdout(output), \
                contextlib.redirect_stderr(errors):
            code = main.main([str(config_path)])
    finally:
        os.chdir(previous)
    return code, output.getvalue(), errors.getvalue()


class BuildTest(unittest.TestCase):
    """Проверяет обход в ширину."""

    def test_bfs_order(self):
        """Пакеты идут по уровням, общая зависимость E — один раз."""
        graph = build(SIMPLE)
        self.assertEqual(graph.packages(), list("ABCDEFG"))
        self.assertEqual(graph.levels["G"], 3)
        self.assertEqual(graph.edges["C"], ["E", "F"])

    def test_max_depth(self):
        """Пакеты на максимальной глубине не раскрываются."""
        graph = build(SIMPLE, depth=1)
        self.assertEqual(graph.packages(), ["A", "B", "C"])
        self.assertTrue(graph.is_expanded("A"))
        self.assertFalse(graph.is_expanded("B"))

    def test_filter(self):
        """Пакеты с подстрокой фильтра не учитываются."""
        graph = build(SIMPLE, filter_text="E")
        self.assertNotIn("E", graph.levels)
        self.assertNotIn("G", graph.levels)
        self.assertEqual(graph.skipped, {"E"})
        self.assertEqual(graph.edges["B"], ["D"])

    def test_cycle_terminates(self):
        """Цикл не приводит к зацикливанию, каждый пакет один раз."""
        graph = build(CYCLE)
        self.assertEqual(graph.packages(), ["A", "B", "C", "D"])
        self.assertEqual(graph.edges["C"], ["A", "D"])

    def test_without_recursion(self):
        """Цепочка длиннее предела рекурсии Python обрабатывается."""
        size = sys.getrecursionlimit() * 2
        chain = {f"P{i}": [f"P{i + 1}"] for i in range(size)}
        graph = build(chain, root="P0", depth=size + 1)
        self.assertEqual(len(graph.levels), size + 1)
        cycles = graph_module.find_cycles(graph.edges, "P0")
        self.assertEqual(cycles, [])


class CycleTest(unittest.TestCase):
    """Проверяет поиск циклических зависимостей."""

    def test_cycles(self):
        """Находится цикл из трёх пакетов и петля."""
        cycles = graph_module.find_cycles(build(CYCLE).edges, "A")
        self.assertIn(["A", "B", "C", "A"], cycles)
        self.assertIn(["D", "D"], cycles)

    def test_no_cycles(self):
        """Ромб (общая зависимость) — не цикл."""
        self.assertEqual(graph_module.find_cycles(SIMPLE, "A"), [])


class FileRepositoryTest(unittest.TestCase):
    """Проверяет файл тестового репозитория."""

    def test_parse(self):
        """Комментарии и пустые строки пропускаются, повторы убираются."""
        text = "# граф\n\nA: B B C\nB:\n"
        self.assertEqual(local_repo.parse_graph(text),
                         {"A": ["B", "C"], "B": []})

    def test_parse_errors(self):
        """Строчные буквы, нет двоеточия, повторное описание."""
        for text in ("A: b", "A B", "A:\nA: B"):
            with self.subTest(text=text):
                with self.assertRaises(cargo.RegistryError):
                    local_repo.parse_graph(text)

    def test_repository(self):
        """Неописанный пакет не имеет зависимостей, корень проверяется."""
        repo = local_repo.FileRepository(str(ROOT / "examples/simple.txt"))
        self.assertEqual(repo.dependencies("A"), ["B", "C"])
        self.assertEqual(repo.dependencies("X"), [])
        with self.assertRaises(cargo.RegistryError):
            repo.check_package("Z")


class MainTest(unittest.TestCase):
    """Проверяет вывод программы на тестовых репозиториях."""

    def test_simple(self):
        """Граф простого репозитория выводится полностью."""
        code, out, _err = run_main(ROOT / "configs/test/simple.xml")
        self.assertEqual(code, 0)
        self.assertIn("B -> D, E", out)
        self.assertIn("Пакетов в графе: 7", out)

    def test_cycle(self):
        """Циклы выводятся отдельным списком."""
        _code, out, _err = run_main(ROOT / "configs/test/cycle.xml")
        self.assertIn("A -> B -> C -> A", out)

    def test_depth_and_filter(self):
        """Ограничение глубины и фильтр видны в выводе."""
        _code, out, _err = run_main(ROOT / "configs/test/depth_2.xml")
        self.assertIn("C -> не анализировался", out)
        _code, out, _err = run_main(ROOT / "configs/test/filter_net.xml")
        self.assertIn("Исключены фильтром: NET", out)
        self.assertNotIn("TLS", out)

    def test_errors(self):
        """Нет пакета и битый файл — код 1 и сообщение."""
        for name in ("not_found", "broken_file"):
            code, _out, err = run_main(ROOT / f"configs/test/{name}.xml")
            self.assertEqual(code, 1)
            self.assertIn("Ошибка получения зависимостей", err)


if __name__ == "__main__":
    unittest.main()
