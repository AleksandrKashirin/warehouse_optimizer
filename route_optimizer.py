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
    access_x: int = -1
    access_y: int = -1
    amount: int = 0  # Новое поле для количества


class RouteOptimizer:
    def __init__(self):
        self.products = {}
        self.placed_products = {}
        self.access_points = {}

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
                    amount=int(row.get("Amount", 0)) if row.get("Amount") else 0,
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
            # Проверяем, есть ли товары с amount > 0
            has_amounts = any(p.amount > 0 for p in self.products.values())
            
            if has_amounts:
                writer.writerow(["ID", "Название", "X", "Y", "Access_X", "Access_Y", "Amount"])
                for product in self.products.values():
                    writer.writerow([
                        product.id, product.name, 
                        product.x, product.y,
                        product.access_x, product.access_y, product.amount
                    ])
            else:
                # Старый формат без Amount
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
        """Генерация случайных выборок товаров (оригинальный метод)"""
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

    def generate_samples_with_limits(
        self, num_samples: int, sample_size: int = 5
    ) -> List[List[str]]:
        """Генерация выборок товаров с учетом ограничений по количеству"""
        available_ids = [id for id in self.access_points.keys() 
                        if self.products[id].amount > 0]

        if len(available_ids) < 1:
            raise ValueError("Нет товаров с доступом и количеством > 0")

        total_capacity = sum(self.products[id].amount for id in available_ids)
        required_total = num_samples * sample_size
        
        if total_capacity < required_total:
            raise ValueError(
                f"Недостаточно общего количества товаров. "
                f"Требуется {required_total}, доступно {total_capacity}"
            )

        # Пытаемся сгенерировать выборки несколько раз
        max_attempts = 10
        for attempt in range(max_attempts):
            try:
                return self._generate_samples_attempt(num_samples, sample_size, available_ids)
            except ValueError:
                if attempt == max_attempts - 1:
                    raise ValueError(f"Не удалось сгенерировать выборки за {max_attempts} попыток")
                continue

    def _generate_samples_attempt(self, num_samples: int, sample_size: int, available_ids: List[str]) -> List[List[str]]:
        """Одна попытка генерации выборок"""
        usage_count = {id: 0 for id in available_ids}
        samples = []

        for sample_idx in range(num_samples):
            sample = []
            sample_count = {}
            
            for pos in range(sample_size):
                # Находим кандидатов с весами (приоритет менее использованным товарам)
                candidates = []
                weights = []
                
                for product_id in available_ids:
                    if usage_count[product_id] >= self.products[product_id].amount:
                        continue
                    if sample_count.get(product_id, 0) >= 3:
                        continue
                    
                    candidates.append(product_id)
                    # Вес обратно пропорционален использованию
                    remaining = self.products[product_id].amount - usage_count[product_id]
                    weight = remaining * 10 + random.random()  # Добавляем случайность
                    weights.append(weight)
                
                if not candidates:
                    raise ValueError(f"Нет кандидатов для выборки {sample_idx + 1}, позиция {pos + 1}")
                
                # Выбираем с учетом весов (приоритет товарам с большим остатком)
                max_weight = max(weights)
                best_candidates = [candidates[i] for i, w in enumerate(weights) if w >= max_weight * 0.8]
                selected_product = random.choice(best_candidates)
                
                sample.append(selected_product)
                usage_count[selected_product] += 1
                sample_count[selected_product] = sample_count.get(selected_product, 0) + 1
            
            samples.append(sample)

        return samples

    def has_amount_data(self) -> bool:
        """Проверка, есть ли данные о количестве товаров"""
        return any(p.amount > 0 for p in self.products.values())

    def get_usage_statistics(self, samples: List[List[str]]) -> Dict[str, int]:
        """Получение статистики использования товаров в выборках"""
        usage_count = {}
        for sample in samples:
            for product_id in sample:
                usage_count[product_id] = usage_count.get(product_id, 0) + 1
        return usage_count

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
                if p.amount > 0:
                    detail["amount"] = p.amount
                info["product_details"].append(detail)

        filepath = f"output/routes/route_{route_id}_info.json"
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(info, f, ensure_ascii=False, indent=2)
        print(f"Информация о маршруте сохранена: {filepath}")

    def export_routes_to_csv(self, filepath: str = "output/routes/routes_summary.csv"):
        """Экспорт всех маршрутов в CSV таблицу"""
        import glob
        import json
        
        route_files = glob.glob("output/routes/route_*_info.json")
        if not route_files:
            raise ValueError("Нет сохраненных маршрутов для экспорта")
        
        routes_data = []
        for file in sorted(route_files):
            with open(file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                routes_data.append(data)
        
        max_products = max(len(route['products']) for route in routes_data)
        
        headers = ["№ Выборки"]
        for i in range(1, max_products + 1):
            headers.extend([f"ID Товара {i}", f"Название товара {i}"])
        headers.append("Длина пути в метрах")
        
        with open(filepath, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            
            for route in routes_data:
                row = [route['route_id']]
                
                for i in range(max_products):
                    if i < len(route['product_details']):
                        product = route['product_details'][i]
                        row.extend([product['id'], product['name']])
                    else:
                        row.extend(["", ""])
                
                row.append(route['distance_meters'])
                writer.writerow(row)
        
        return len(routes_data)