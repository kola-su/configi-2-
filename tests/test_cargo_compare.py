"""Тесты сравнения порядка загрузки с настоящим Cargo."""

import contextlib
import importlib
import io
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

compare = importlib.import_module("cargo_compare")

HAS_CARGO = shutil.which("cargo") is not None


class ManifestTest(unittest.TestCase):
    """Проверяет создание workspace Cargo из тестового графа."""

    def test_manifest(self):
        """Зависимости записываются через path, имена строчными."""
        text = compare.crate_manifest("APP", ["CORE"])
        self.assertIn('name = "app"', text)
        self.assertIn('core = { path = "../core" }', text)

    def test_workspace(self):
        """Создаётся крейт для каждого пакета, включая листья."""
        with tempfile.TemporaryDirectory() as folder:
            compare.write_workspace({"A": ["B"]}, Path(folder))
            names = sorted(path.name for path in Path(folder).iterdir())
        self.assertEqual(names, ["Cargo.toml", "a", "b"])


@unittest.skipUnless(HAS_CARGO, "Cargo не установлен")
class CargoTest(unittest.TestCase):
    """Запускает настоящий Cargo без доступа к сети."""

    def test_chain_matches(self):
        """На цепочке порядок Cargo совпадает с порядком визуализатора."""
        output = io.StringIO()
        with tempfile.TemporaryDirectory() as folder, \
                contextlib.redirect_stdout(output):
            code = compare.main([str(ROOT / "examples/chain.txt"), "A",
                                 "--out", folder])
        self.assertEqual(code, 0)
        self.assertIn("Совпадает", output.getvalue())

    def test_cycle_rejected(self):
        """Цикл Cargo не принимает: возвращается ошибка."""
        with tempfile.TemporaryDirectory() as folder:
            compare.write_workspace({"A": ["B"], "B": ["A"]}, Path(folder))
            order, error = compare.cargo_build_order(Path(folder), "A")
        self.assertIsNone(order)
        self.assertIn("cyclic package dependency", error)


if __name__ == "__main__":
    unittest.main()
