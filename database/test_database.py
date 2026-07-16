"""Testes do database manager."""

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")


class TestDatabaseManager(unittest.TestCase):
    def test_save_and_load_products(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "products.json"

            with patch("database.database_manager.DATABASE_FILE", str(db_path)):
                from database.database_manager import save_product, load_products

                produto = {
                    "produto": {"nome": "Teste AI-Commerce"},
                    "analise": {"score": 90, "potencial": "alto"},
                }

                save_product(produto)
                products = load_products()

            self.assertEqual(len(products), 1)
            self.assertEqual(products[0]["produto"]["nome"], "Teste AI-Commerce")


if __name__ == "__main__":
    unittest.main()
