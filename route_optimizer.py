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
        """Экспорт всех маршрутов в упрощенный CSV"""
        import glob
        import json
        
        route_files = glob.glob("output/routes/route_*_info.json")
        if not route_files:
            raise ValueError("Нет сохраненных маршрутов для экспорта")
        
        routes_data = []
        for file in sorted(route_files, key=lambda x: int(x.split('_')[1])):
            with open(file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                routes_data.append(data)
        
        max_products = max(len(route['products']) for route in routes_data)
        
        # Упрощенные заголовки - только ID товаров
        headers = ["№ Выборки"]
        for i in range(1, max_products + 1):
            headers.append(f"Товар {i}")
        
        with open(filepath, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            
            for route in routes_data:
                row = [route['route_id']]
                
                # Только ID товаров
                for i in range(max_products):
                    if i < len(route['products']):
                        row.append(route['products'][i])
                    else:
                        row.append("")
                
                writer.writerow(row)
        
        return len(routes_data)
    
    def optimize_samples_order(self, samples: List[List[str]], group_size: int = 15) -> List[List[str]]:
        """Улучшенная оптимизация порядка выборок"""
        if not samples:
            return samples
        
        # Разбиваем на группы (ночи) и оптимизируем каждую отдельно
        groups = []
        for i in range(0, len(samples), group_size):
            group = samples[i:i + group_size]
            groups.append(group)
        
        optimized_groups = []
        for group_idx, group in enumerate(groups):
            print(f"Оптимизирую ночь {group_idx + 1}: {len(group)} выборок...")
            optimized_group = self._optimize_single_group(group)
            optimized_groups.append(optimized_group)
        
        # Объединяем обратно
        result = []
        for group in optimized_groups:
            result.extend(group)
        
        return result

    def _optimize_single_group(self, samples: List[List[str]]) -> List[List[str]]:
        """Оптимизация одной группы (ночи)"""
        if len(samples) <= 1:
            return samples
        
        best_order = None
        best_score = float('inf')
        
        # Пробуем несколько разных стартовых точек
        num_attempts = min(len(samples), 5)  # Не больше 5 попыток
        for attempt in range(num_attempts):
            # Жадный алгоритм с разными стартовыми точками
            current_order = self._greedy_optimize_group(samples, start_idx=attempt)
            
            # Локальные улучшения (2-opt)
            improved_order = self._local_improvement_2opt(current_order)
            
            # Оцениваем качество
            score = self._calculate_group_score(improved_order)
            
            if score < best_score:
                best_score = score
                best_order = improved_order
        
        return best_order

    def _greedy_optimize_group(self, samples: List[List[str]], start_idx: int = 0) -> List[List[str]]:
        """Жадный алгоритм для одной группы с выбором стартовой точки"""
        if not samples:
            return samples
        
        optimized = []
        remaining = samples.copy()
        
        # Начинаем с лучшей стартовой точки
        if start_idx < len(remaining):
            current = remaining.pop(start_idx)
        else:
            current = remaining.pop(0)
        optimized.append(current)
        
        while remaining:
            best_next = None
            best_overlap = -1
            best_index = -1
            
            # Ищем выборку с максимальным пересечением
            for i, candidate in enumerate(remaining):
                overlap = len(set(current) & set(candidate))
                if overlap > best_overlap:
                    best_overlap = overlap
                    best_next = candidate
                    best_index = i
            
            if best_next is not None:
                current = remaining.pop(best_index)
                optimized.append(current)
            else:
                current = remaining.pop(0)
                optimized.append(current)
        
        return optimized

    def _local_improvement_2opt(self, samples: List[List[str]]) -> List[List[str]]:
        """Локальные улучшения методом 2-opt"""
        improved = samples.copy()
        n = len(improved)
        
        if n <= 2:
            return improved
        
        improved_found = True
        while improved_found:
            improved_found = False
            current_score = self._calculate_group_score(improved)
            
            # Пробуем все возможные обмены соседних пар
            for i in range(n - 1):
                for j in range(i + 2, min(i + 6, n)):  # Ограничиваем область поиска
                    # Пробуем обратить участок от i до j
                    new_order = improved.copy()
                    new_order[i:j+1] = reversed(new_order[i:j+1])
                    
                    new_score = self._calculate_group_score(new_order)
                    if new_score < current_score:
                        improved = new_order
                        current_score = new_score
                        improved_found = True
                        break
                
                if improved_found:
                    break
        
        return improved

    def _calculate_group_score(self, samples: List[List[str]]) -> float:
        """Вычисляет общий счет группы (меньше = лучше)"""
        if len(samples) <= 1:
            return 0
        
        total_changes = 0
        for i in range(len(samples) - 1):
            try:
                current_set = set(samples[i])
                next_set = set(samples[i + 1])
                # Количество изменений = товары которые нужно убрать + товары которые нужно добавить
                changes = len(current_set - next_set) + len(next_set - current_set)
                total_changes += changes
            except TypeError as e:
                # Если ошибка с типами, выводим отладочную информацию
                print(f"Ошибка в _calculate_group_score: {e}")
                print(f"samples[{i}]: {samples[i]}")
                print(f"samples[{i+1}]: {samples[i+1]}")
                print(f"Тип samples[{i}][0]: {type(samples[i][0]) if samples[i] else 'empty'}")
                raise
        
        return total_changes

    def group_samples_by_nights(self, samples: List[List[str]], group_size: int = 15) -> List[List[List[str]]]:
        """Разбивка выборок на группы (ночи)"""
        groups = []
        for i in range(0, len(samples), group_size):
            group = samples[i:i + group_size]
            groups.append(group)
        return groups
    
    def save_config(self, config_path: str = "data/last_config.json"):
        """Сохранение текущей конфигурации"""
        config = {
            "map_path": getattr(self, 'current_map_path', ''),
            "products_path": getattr(self, 'current_products_path', ''),
            "markup_path": getattr(self, 'current_markup_path', ''),
            "start_point": getattr(self, 'start_point', None),
            "end_point": getattr(self, 'end_point', None),
            "scale_set": getattr(self, 'scale_set', False),
            "robot_radius_set": getattr(self, 'robot_radius_set', False)
        }
        
        Path("data").mkdir(exist_ok=True)
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)

    def load_config(self, config_path: str = "data/last_config.json") -> Dict:
        """Загрузка конфигурации"""
        if not Path(config_path).exists():
            return {}
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}

    def analyze_night_efficiency(self, groups: List[List[List[str]]]) -> Dict:
        """Анализ эффективности группировки по ночам"""
        stats = {
            'nights': [],
            'total_unique_products': 0,
            'avg_products_per_night': 0,
            'efficiency_score': 0
        }
        
        all_products = set()
        night_products_counts = []
        total_changes = 0
        total_possible_changes = 0
        
        for night_idx, night_samples in enumerate(groups):
            night_products = set()
            night_changes = 0
            
            for sample in night_samples:
                night_products.update(sample)
            
            # Считаем изменения между соседними выборками
            for i in range(len(night_samples) - 1):
                current_set = set(night_samples[i])
                next_set = set(night_samples[i + 1])
                # Изменения = убрать + добавить
                changes = len(current_set - next_set) + len(next_set - current_set)
                night_changes += changes
            
            # Максимально возможные изменения для этой ночи
            max_changes_night = (len(night_samples) - 1) * 10  # Если бы все товары были разные
            
            night_info = {
                'night': night_idx + 1,
                'experiments': len(night_samples),
                'unique_products': len(night_products),
                'total_changes': night_changes,
                'max_possible_changes': max_changes_night,
                'efficiency': 1 - (night_changes / max_changes_night) if max_changes_night > 0 else 1,
                'avg_changes_per_experiment': night_changes / (len(night_samples) - 1) if len(night_samples) > 1 else 0,
                'products': sorted(list(night_products))
            }
            
            stats['nights'].append(night_info)
            all_products.update(night_products)
            night_products_counts.append(len(night_products))
            total_changes += night_changes
            total_possible_changes += max_changes_night
        
        stats['total_unique_products'] = len(all_products)
        stats['avg_products_per_night'] = sum(night_products_counts) / len(night_products_counts) if night_products_counts else 0
        stats['efficiency_score'] = 1 - (total_changes / total_possible_changes) if total_possible_changes > 0 else 1
        
        return stats
    
    def export_distances_to_csv(self, filepath: str = "output/routes/distances_summary.csv"):
        """Экспорт дистанций между точками маршрутов в CSV"""
        import glob
        import json
        
        route_files = glob.glob("output/routes/route_*_info.json")
        if not route_files:
            raise ValueError("Нет сохраненных маршрутов для экспорта")
        
        routes_data = []
        for file in sorted(route_files, key=lambda x: int(x.split('_')[1])):
            with open(file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                routes_data.append(data)
        
        # Заголовки для дистанций между точками
        headers = [
            "№ Выборки",
            "Старт→Товар1", 
            "Товар1→Товар2",
            "Товар2→Товар3", 
            "Товар3→Товар4",
            "Товар4→Товар5",
            "Товар5→Финиш",
            "Общая дистанция"
        ]
        
        with open(filepath, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            
            for route in routes_data:
                route_id = route['route_id']
                total_distance = route['distance_meters']
                
                # Загружаем полный путь из отдельного файла если есть
                path_file = f"output/routes/route_{route_id}_path.json"
                segment_distances = []
                
                if Path(path_file).exists():
                    # Если есть детальный путь, вычисляем по сегментам
                    with open(path_file, 'r', encoding='utf-8') as pf:
                        path_data = json.load(pf)
                        segments = path_data.get('segments', [])
                        for segment in segments:
                            segment_distances.append(round(segment.get('distance', 0), 2))
                else:
                    # Если нет детального пути, равномерно распределяем общую дистанцию
                    num_products = len(route['products'])
                    segments_count = num_products + 1  # старт→товар1, товар1→товар2, ..., товарN→финиш
                    avg_distance = total_distance / segments_count if segments_count > 0 else 0
                    segment_distances = [round(avg_distance, 2)] * segments_count
                
                # Дополняем до 6 сегментов если меньше
                while len(segment_distances) < 6:
                    segment_distances.append(0)
                
                # Обрезаем если больше 6
                segment_distances = segment_distances[:6]
                
                row = [route_id] + segment_distances + [round(total_distance, 2)]
                writer.writerow(row)
        
        return len(routes_data)