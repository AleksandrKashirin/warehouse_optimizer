import csv
import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple


@dataclass
class Product:
    id: str
    name: str
    x: int = -1
    y: int = -1
    access_x: int = -1  # Добавляем точку доступа
    access_y: int = -1


class RouteOptimizer:
    def __init__(self):
        self.products = {}
        self.placed_products = {}
        self.access_points = {}  # Добавляем словарь точек доступа

    def load_products(self, filepath: str):
        """Загрузка товаров из CSV"""
        self.products.clear()
        self.placed_products.clear()
        self.access_points.clear()
        
        with open(filepath, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                product = Product(
                    id=row["ID"],
                    name=row["Название"],
                    x=int(row.get("X", -1)) if row.get("X") else -1,
                    y=int(row.get("Y", -1)) if row.get("Y") else -1,
                    access_x=int(row.get("Access_X", -1)) if row.get("Access_X") else -1,
                    access_y=int(row.get("Access_Y", -1)) if row.get("Access_Y") else -1,
                )
                self.products[product.id] = product
                if product.x >= 0 and product.y >= 0:
                    self.placed_products[product.id] = (product.x, product.y)
                    if product.access_x >= 0 and product.access_y >= 0:
                        self.access_points[product.id] = (product.access_x, product.access_y)

    def save_products(self, filepath: str):
        """Сохранение товаров с координатами и точками доступа"""
        with open(filepath, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["ID", "Название", "X", "Y", "Access_X", "Access_Y"])
            for product in self.products.values():
                writer.writerow([
                    product.id, product.name, 
                    product.x, product.y,
                    product.access_x, product.access_y
                ])

    def place_product(self, product_id: str, x: int, y: int, access_point: Tuple[int, int] = None):
        """Размещение товара на карте с точкой доступа"""
        if product_id in self.products:
            self.products[product_id].x = x
            self.products[product_id].y = y
            self.placed_products[product_id] = (x, y)
            
            if access_point:
                self.products[product_id].access_x = access_point[0]
                self.products[product_id].access_y = access_point[1]
                self.access_points[product_id] = access_point

    def get_product_at(self, x: int, y: int, tolerance: int = 5) -> Product:
        """Получение товара по координатам"""
        for product in self.products.values():
            if product.x >= 0 and product.y >= 0:
                if abs(product.x - x) <= tolerance and abs(product.y - y) <= tolerance:
                    return product
        return None

    def generate_samples(
        self, num_samples: int, sample_size: int = 5
    ) -> List[List[str]]:
        """Генерация случайных выборок товаров"""
        # Используем только товары с точками доступа
        placed_ids = [id for id in self.access_points.keys()]

        if len(placed_ids) < sample_size:
            raise ValueError(
                f"Недостаточно размещенных товаров с точками доступа. Нужно минимум {sample_size}, есть {len(placed_ids)}"
            )

        samples = []
        for _ in range(num_samples):
            sample = random.sample(placed_ids, sample_size)
            samples.append(sample)

        return samples

    def get_access_coordinates(self, product_ids: List[str]) -> List[Tuple[int, int]]:
        """Получение точек доступа для списка товаров"""
        coords = []
        for pid in product_ids:
            if pid in self.access_points:
                coords.append(self.access_points[pid])
        return coords

    def get_product_coordinates(self, product_ids: List[str]) -> List[Tuple[int, int]]:
        """Получение координат для списка товаров"""
        coords = []
        for pid in product_ids:
            if pid in self.placed_products:
                coords.append(self.placed_products[pid])
        return coords

    def save_route_info(
        self,
        route_id: int,
        products: List[str],
        distance: float,
        path: List[Tuple[int, int]],
    ):
        """Сохранение информации о маршруте"""
        # Убедимся, что директория существует
        Path("output/routes").mkdir(parents=True, exist_ok=True)

        info = {
            "route_id": route_id,
            "products": products,
            "distance_meters": round(distance, 2),
            "path_length": len(path),
            "product_details": [],
        }

        for pid in products:
            if pid in self.products:
                p = self.products[pid]
                detail = {
                    "id": p.id, 
                    "name": p.name, 
                    "coordinates": [p.x, p.y]
                }
                if pid in self.access_points:
                    detail["access_point"] = list(self.access_points[pid])
                info["product_details"].append(detail)

        filepath = f"output/routes/route_{route_id}_info.json"
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(info, f, ensure_ascii=False, indent=2)
        print(f"Информация о маршруте сохранена: {filepath}")