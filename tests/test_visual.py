"""Тесты визуализации: ASCII-дерево, язык DOT и изображение SVG."""

import importlib
import shutil
import sys
import tempfile
import unittest
import xml.etree.ElementTree as xml_tree
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

graph_module = importlib.import_module("graph")
svg = importlib.import_module("svg")
visual = importlib.import_module("visual")

SIMPLE = {"A": ["B", "C"], "B": ["D", "E"], "C": ["E", "F"], "E": ["G"]}
CYCLE = {"A": ["B"], "B": ["C"], "C": ["A", "D"], "D": ["D"]}
HAS_DOT = shutil.which("dot") is not None


def build(edges, depth=10, root="A"):
    """Строит граф по словарю и возвращает его вместе с циклами."""
    graph = graph_module.build_graph(root, lambda n: edges.get(n, []), depth)
    return graph, graph_module.find_cycles(graph.edges, root)


class AsciiTreeTest(unittest.TestCase):
    """Проверяет ASCII-дерево."""

    def test_simple(self):
        """Повторный пакет помечается (*) и не раскрывается."""
        graph, _cycles = build(SIMPLE)
        expected = "\n".join([
            "A", "├── B", "│   ├── D", "│   └── E", "│       └── G",
            "└── C", "    ├── E (*)", "    └── F"])
        self.assertEqual(visual.ascii_tree(graph), expected)

    def test_cycle_and_depth(self):
        """Цикл помечается (цикл), обрезка глубиной — (...)."""
        graph, _cycles = build(CYCLE)
        tree = visual.ascii_tree(graph)
        self.assertIn("├── A (цикл)", tree)
        self.assertIn("└── D (цикл)", tree)
        graph, _cycles = build(SIMPLE, depth=1)
        self.assertEqual(visual.ascii_tree(graph),
                         "A\n├── B (...)\n└── C (...)")


class DotTest(unittest.TestCase):
    """Проверяет описание графа на языке Graphviz."""

    def test_structure(self):
        """Все рёбра на месте, корень выделен."""
        graph, cycles = build(SIMPLE)
        source = visual.dot_source(graph, cycles)
        self.assertTrue(source.startswith("digraph dependencies {"))
        self.assertTrue(source.endswith("}"))
        self.assertIn('"A" [fillcolor="#ffd8a8", penwidth=2];', source)
        self.assertEqual(source.count(" -> "), 7)

    def test_cycles_depth_quotes(self):
        """Рёбра циклов красные, обрезанные узлы пунктиром, кавычки."""
        graph, cycles = build(CYCLE)
        source = visual.dot_source(graph, cycles)
        self.assertIn('"C" -> "A" [color="#d62828", penwidth=2];', source)
        self.assertIn('"C" -> "D";', source)
        graph, cycles = build({"A": ['x"y']}, depth=1)
        source = visual.dot_source(graph, cycles)
        self.assertIn('"x\\"y" [style="rounded,filled,dashed"];', source)


class SvgTest(unittest.TestCase):
    """Проверяет сохранение изображения в формате SVG."""

    def check_svg(self, path):
        """Файл — корректный XML с корнем svg и подписями пакетов."""
        root = xml_tree.parse(path).getroot()
        self.assertTrue(root.tag.endswith("svg"))
        self.assertIn(">G<", Path(path).read_text(encoding="utf-8"))

    def test_builtin(self):
        """Без Graphviz изображение рисует встроенный модуль."""
        graph, cycles = build(SIMPLE)
        with tempfile.TemporaryDirectory() as folder, \
                mock.patch.object(visual.shutil, "which", return_value=None):
            path = str(Path(folder) / "out" / "graph.svg")
            self.assertEqual(visual.save_svg(graph, cycles, path),
                             "встроенная отрисовка")
            self.check_svg(path)

    @unittest.skipUnless(HAS_DOT, "Graphviz не установлен")
    def test_graphviz(self):
        """С Graphviz изображение строит программа dot."""
        graph, cycles = build(SIMPLE)
        with tempfile.TemporaryDirectory() as folder:
            path = str(Path(folder) / "graph.svg")
            self.assertEqual(visual.save_svg(graph, cycles, path),
                             "Graphviz dot")
            self.check_svg(path)

    def test_layers(self):
        """Слой — самый длинный путь от корня, циклы не учитываются."""
        graph, _cycles = build({"A": ["B", "C"], "B": ["C"], "C": ["A"]})
        self.assertEqual(svg.layer_numbers(graph), {"A": 0, "B": 1, "C": 2})

    def test_cycle_drawing(self):
        """Рёбра циклов рисуются отдельным красным наконечником."""
        graph, cycles = build(CYCLE)
        text = svg.draw_svg(graph, visual.cycle_edges(cycles))
        self.assertEqual(text.count('marker-end="url(#cycle)"'), 4)
        xml_tree.fromstring(text)


if __name__ == "__main__":
    unittest.main()
