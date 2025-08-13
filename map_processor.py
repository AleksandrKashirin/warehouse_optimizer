import heapq
from typing import List, Optional, Tuple

import numpy as np
from PIL import Image


class MapProcessor:
    def __init__(self):
        self.grid = None
        self.scale = 0.1  # метров на пиксель (по умолчанию 10см на пиксель)
        self.robot_radius_meters = 0.3  # радиус робота в метрах (по умолчанию 30см)
        self.robot_radius_pixels = 3  # будет пересчитан после установки масштаба
        self.width = 0
        self.height = 0
        
    def load_map(self, filepath: str) -> np.ndarray:
        """Загрузка BMP карты и преобразование в сетку"""
        img = Image.open(filepath).convert('L')
        self.width, self.height = img.size
        
        # Преобразование в массив (0 - проходимо, 1 - препятствие)
        img_array = np.array(img)
        self.original_grid = (img_array < 128).astype(int)  # черный = препятствие
        
        # Пересчет радиуса робота в пиксели
        self._update_robot_radius_pixels()
        
        # Расширяем препятствия на радиус робота
        self.grid = self._expand_obstacles(self.original_grid)
        
        return self.grid
    
    def _expand_obstacles(self, grid: np.ndarray) -> np.ndarray:
        """Расширение препятствий на радиус робота"""
        if self.robot_radius_pixels <= 1:
            return grid
        
        expanded = grid.copy()
        r = self.robot_radius_pixels
        
        # Находим все препятствия
        obstacles = np.where(grid == 1)
        
        # Расширяем каждое препятствие
        for y, x in zip(obstacles[0], obstacles[1]):
            # Расширяем в квадрате вокруг препятствия
            y_min = max(0, y - r)
            y_max = min(self.height, y + r + 1)
            x_min = max(0, x - r)
            x_max = min(self.width, x + r + 1)
            
            expanded[y_min:y_max, x_min:x_max] = 1
        
        print(f"DEBUG: Препятствия расширены на {r} пикселей")
        return expanded
    
    def set_scale(self, pixel_distance: float, real_distance: float):
        """Установка масштаба карты"""
        if pixel_distance > 0:
            self.scale = real_distance / pixel_distance
            self._update_robot_radius_pixels()
    
    def set_robot_radius_meters(self, radius_meters: float):
        """Установка радиуса робота в метрах"""
        self.robot_radius_meters = radius_meters
        self._update_robot_radius_pixels()
        # Пересчитываем препятствия с новым радиусом если карта уже загружена
        if hasattr(self, 'original_grid'):
            self.grid = self._expand_obstacles(self.original_grid)
    
    def _update_robot_radius_pixels(self):
        """Пересчет радиуса робота из метров в пиксели"""
        if self.scale > 0:
            self.robot_radius_pixels = max(1, int(self.robot_radius_meters / self.scale))
        else:
            self.robot_radius_pixels = 3
    
    def _update_robot_radius_pixels(self):
        """Пересчет радиуса робота из метров в пиксели"""
        if self.scale > 0:
            self.robot_radius_pixels = max(1, int(self.robot_radius_meters / self.scale))
        else:
            self.robot_radius_pixels = 3
    
    def is_walkable(self, x: int, y: int, check_radius: bool = True) -> bool:
        """Проверка проходимости точки"""
        if not (0 <= x < self.width and 0 <= y < self.height):
            return False
        
        # Базовая проверка - точка должна быть в проходе
        if self.grid[y, x] == 1:
            return False
        
        if not check_radius:
            return True
        
        # Проверка с учетом радиуса робота (исправлено)
        r = self.robot_radius_pixels
        
        # Проверяем ключевые точки вокруг робота
        for dx in [-r, 0, r]:
            for dy in [-r, 0, r]:
                nx, ny = x + dx, y + dy
                # Проверяем только точки внутри карты
                if 0 <= nx < self.width and 0 <= ny < self.height:
                    if self.grid[ny, nx] == 1:
                        return False
                # Точки за границей карты не блокируют проход
        
        return True
    
    def is_shelf(self, x: int, y: int) -> bool:
        """Проверка, является ли точка стеллажом (используем оригинальную сетку)"""
        if 0 <= x < self.width and 0 <= y < self.height:
            if hasattr(self, 'original_grid'):
                return self.original_grid[y, x] == 1
            else:
                return self.grid[y, x] == 1
        return False
    
    def find_nearest_walkable(self, x: int, y: int, max_radius: int = 50) -> Optional[Tuple[int, int]]:
        """Поиск ближайшей проходимой точки"""
        # Если точка уже проходима
        if self.is_walkable(x, y, check_radius=False):
            return (x, y)
        
        # Поиск по кольцам от точки (действительно ближайшая)
        for r in range(1, max_radius):
            candidates = []
            # Собираем все точки на расстоянии r
            for dx in range(-r, r + 1):
                for dy in range(-r, r + 1):
                    if abs(dx) == r or abs(dy) == r:  # Только точки на границе кольца
                        nx, ny = x + dx, y + dy
                        if self.is_walkable(nx, ny, check_radius=False):
                            # Вычисляем реальное расстояние
                            dist = (dx * dx + dy * dy) ** 0.5
                            candidates.append((dist, nx, ny))
            
            # Возвращаем ближайшую из найденных
            if candidates:
                candidates.sort()
                return (candidates[0][1], candidates[0][2])
        
        return None
    
    def save_map_metadata(self, map_filepath: str):
        """Сохранение метаданных карты"""
        import json
        from pathlib import Path
        
        metadata = {
            "map_file": map_filepath,
            "scale": self.scale,
            "robot_radius_meters": self.robot_radius_meters,
            "robot_radius_pixels": self.robot_radius_pixels,
            "width": self.width,
            "height": self.height
        }
        
        # Сохраняем рядом с картой
        map_path = Path(map_filepath)
        metadata_path = map_path.parent / f"{map_path.stem}_metadata.json"
        
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        
        print(f"Метаданные карты сохранены: {metadata_path}")
    
    def load_map_metadata(self, map_filepath: str) -> bool:
        """Загрузка метаданных карты"""
        import json
        from pathlib import Path
        
        map_path = Path(map_filepath)
        metadata_path = map_path.parent / f"{map_path.stem}_metadata.json"
        
        if not metadata_path.exists():
            print(f"Файл метаданных не найден: {metadata_path}")
            return False
        
        try:
            with open(metadata_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            
            self.scale = metadata.get("scale", 0.1)
            self.robot_radius_meters = metadata.get("robot_radius_meters", 0.3)
            self.robot_radius_pixels = metadata.get("robot_radius_pixels", 3)
            
            print(f"Метаданные карты загружены: масштаб={self.scale:.4f}, радиус={self.robot_radius_meters}м")
            return True
            
        except Exception as e:
            print(f"Ошибка загрузки метаданных: {e}")
            return False
    
    def a_star(self, start: Tuple[int, int], goal: Tuple[int, int]) -> Optional[List[Tuple[int, int]]]:
        """Алгоритм A* для поиска пути (упрощенный)"""
        print(f"DEBUG A*: Поиск пути от {start} к {goal}")
        
        # Простая проверка проходимости без радиуса
        start_walkable = self.is_walkable(*start, check_radius=False)
        goal_walkable = self.is_walkable(*goal, check_radius=False)
        
        print(f"DEBUG A*: Старт проходим: {start_walkable}, Финиш проходим: {goal_walkable}")
        
        if not start_walkable or not goal_walkable:
            print(f"DEBUG A*: Путь невозможен - непроходимые точки")
            return None
        
        def heuristic(a, b):
            return abs(a[0] - b[0]) + abs(a[1] - b[1])
        
        open_set = []
        heapq.heappush(open_set, (0, start))
        came_from = {}
        g_score = {start: 0}
        
        directions = [(0, 1), (1, 0), (0, -1), (-1, 0)]
        
        max_iterations = self.width * self.height // 4
        iterations = 0
        
        while open_set and iterations < max_iterations:
            iterations += 1
            current = heapq.heappop(open_set)[1]
            
            if current == goal:
                print(f"DEBUG A*: Путь найден за {iterations} итераций")
                # Восстановление пути
                path = []
                while current in came_from:
                    path.append(current)
                    current = came_from[current]
                path.append(start)
                result_path = path[::-1]
                print(f"DEBUG A*: Длина пути: {len(result_path)} точек")
                return result_path
            
            for dx, dy in directions:
                neighbor = (current[0] + dx, current[1] + dy)
                
                # Только базовая проверка проходимости без радиуса робота
                if not self.is_walkable(*neighbor, check_radius=False):
                    continue
                
                tentative_g = g_score[current] + 1
                
                if neighbor not in g_score or tentative_g < g_score[neighbor]:
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g
                    f_score = tentative_g + heuristic(neighbor, goal)
                    heapq.heappush(open_set, (f_score, neighbor))
        
        print(f"DEBUG A*: Путь НЕ найден после {iterations} итераций")
        return None
    
    def compute_distance_matrix(self, points: List[Tuple[int, int]], 
                               start: Tuple[int, int], 
                               end: Tuple[int, int]) -> dict:
        """Предварительный расчет матрицы расстояний между всеми точками (с отладкой)"""
        n = len(points)
        distances = {}
        
        print(f"DEBUG MATRIX: Вычисление матрицы для {n} точек")
        
        # От старта ко всем точкам
        for i, point in enumerate(points):
            print(f"DEBUG MATRIX: Поиск пути от старта {start} к точке {i}: {point}")
            path = self.a_star(start, point)
            dist = len(path) - 1 if path else float('inf')
            distances[('start', i)] = dist
            print(f"DEBUG MATRIX: Расстояние от старта к точке {i}: {dist}")
        
        # Между всеми точками (только уникальные пары)
        for i in range(n):
            for j in range(i + 1, n):
                print(f"DEBUG MATRIX: Поиск пути между точками {i}: {points[i]} и {j}: {points[j]}")
                path = self.a_star(points[i], points[j])
                dist = len(path) - 1 if path else float('inf')
                distances[(i, j)] = dist
                distances[(j, i)] = dist  # Симметричность
                print(f"DEBUG MATRIX: Расстояние между точками {i} и {j}: {dist}")
        
        # От всех точек к финишу
        for i, point in enumerate(points):
            print(f"DEBUG MATRIX: Поиск пути от точки {i}: {point} к финишу {end}")
            path = self.a_star(point, end)
            dist = len(path) - 1 if path else float('inf')
            distances[(i, 'end')] = dist
            print(f"DEBUG MATRIX: Расстояние от точки {i} к финишу: {dist}")
        
        # Выводим итоговую матрицу
        print("DEBUG MATRIX: Итоговая матрица расстояний:")
        for key, value in distances.items():
            print(f"  {key}: {value}")
        
        return distances
    
    def find_optimal_route_simple(self, start: Tuple[int, int], 
                                 points: List[Tuple[int, int]], 
                                 end: Tuple[int, int]) -> Tuple[List[Tuple[int, int]], float, List[int]]:
        """Упрощенный поиск оптимального маршрута для небольшого количества точек (с отладкой)"""
        from itertools import permutations
        
        n = len(points)
        print(f"DEBUG ROUTE: Поиск маршрута для {n} точек")
        print(f"DEBUG ROUTE: Старт: {start}, Финиш: {end}")
        print(f"DEBUG ROUTE: Точки: {points}")
        
        if n == 0:
            print("DEBUG ROUTE: Нет точек, ищем прямой путь")
            path = self.a_star(start, end)
            if path:
                return path, (len(path) - 1) * self.scale, []
            return [], float('inf'), []
        
        if n > 7:
            print("DEBUG ROUTE: Много точек, используем жадный алгоритм")
            # Для большого количества точек используем жадный алгоритм
            return self.find_greedy_route(start, points, end)
        
        print("DEBUG ROUTE: Вычисляем матрицу расстояний")
        # Вычисляем матрицу расстояний
        distances = self.compute_distance_matrix(points, start, end)
        
        # Проверим доступность всех точек
        invalid_points = []
        for i, point in enumerate(points):
            if distances[('start', i)] == float('inf'):
                invalid_points.append(i)
            if distances[(i, 'end')] == float('inf'):
                invalid_points.append(i)
        
        if invalid_points:
            print(f"DEBUG ROUTE: Недоступные точки: {[points[i] for i in invalid_points]}")
            return [], float('inf'), []
        
        print("DEBUG ROUTE: Все точки доступны, ищем оптимальный порядок")
        
        best_distance = float('inf')
        best_order = None
        
        # Перебираем все перестановки для малого количества точек
        for perm in permutations(range(n)):
            total_dist = distances[('start', perm[0])]
            
            if total_dist == float('inf'):
                continue
            
            valid = True
            for i in range(n - 1):
                dist = distances.get((perm[i], perm[i + 1]), float('inf'))
                if dist == float('inf'):
                    valid = False
                    break
                total_dist += dist
            
            if not valid:
                continue
            
            total_dist += distances[(perm[-1], 'end')]
            
            if total_dist < best_distance:
                best_distance = total_dist
                best_order = list(perm)
        
        if best_order is None:
            print("DEBUG ROUTE: Не найден валидный порядок точек")
            return [], float('inf'), []
        
        print(f"DEBUG ROUTE: Найден оптимальный порядок: {best_order}, расстояние: {best_distance}")
        
        # Восстанавливаем полный путь
        full_path = []
        
        path = self.a_star(start, points[best_order[0]])
        if path:
            full_path.extend(path[:-1])
        else:
            print("DEBUG ROUTE: Не удалось построить путь от старта к первой точке")
            return [], float('inf'), []
        
        for i in range(len(best_order) - 1):
            path = self.a_star(points[best_order[i]], points[best_order[i + 1]])
            if path:
                full_path.extend(path[:-1])
            else:
                print(f"DEBUG ROUTE: Не удалось построить путь между точками {best_order[i]} и {best_order[i + 1]}")
                return [], float('inf'), []
        
        path = self.a_star(points[best_order[-1]], end)
        if path:
            full_path.extend(path)
        else:
            print("DEBUG ROUTE: Не удалось построить путь от последней точки к финишу")
            return [], float('inf'), []
        
        print(f"DEBUG ROUTE: Полный путь построен, {len(full_path)} точек")
        return full_path, best_distance * self.scale, best_order
    
    def find_greedy_route(self, start: Tuple[int, int], 
                         points: List[Tuple[int, int]], 
                         end: Tuple[int, int]) -> Tuple[List[Tuple[int, int]], float, List[int]]:
        """Жадный алгоритм для большого количества точек"""
        n = len(points)
        unvisited = set(range(n))
        current_pos = start
        order = []
        full_path = []
        total_distance = 0
        
        while unvisited:
            best_next = None
            best_dist = float('inf')
            best_path = None
            
            # Находим ближайшую непосещенную точку
            for i in unvisited:
                path = self.a_star(current_pos, points[i])
                if path:
                    dist = len(path) - 1
                    if dist < best_dist:
                        best_dist = dist
                        best_next = i
                        best_path = path
            
            if best_next is None:
                return [], float('inf'), []
            
            # Добавляем путь
            if best_path:
                if full_path:
                    full_path.extend(best_path[:-1])
                else:
                    full_path.extend(best_path[:-1])
                total_distance += best_dist
            
            order.append(best_next)
            unvisited.remove(best_next)
            current_pos = points[best_next]
        
        # Путь к финишу
        path = self.a_star(current_pos, end)
        if path:
            full_path.extend(path)
            total_distance += len(path) - 1
        else:
            return [], float('inf'), []
        
        return full_path, total_distance * self.scale, order