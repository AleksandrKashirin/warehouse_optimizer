import heapq
import json
from typing import List, Optional, Tuple

import numpy as np
from PIL import Image, ImageDraw


class MapProcessor:
    def __init__(self):
        self.grid = None
        self.scale = 0.1
        self.robot_radius_meters = 0.3
        self.robot_radius_pixels = 3
        self.width = 0
        self.height = 0
        self.original_image = None  # Исходное изображение
        self.walls = []  # Список стен [(x1,y1,x2,y2), ...]
        self.shelves = []  # Список стеллажей [(x1,y1,x2,y2), ...]
        
    def load_map(self, filepath: str) -> np.ndarray:
        """Загрузка изображения карты (PNG/JPG/BMP)"""
        img = Image.open(filepath).convert('RGB')
        self.width, self.height = img.size
        self.original_image = img.copy()
        
        # Создаем пустую сетку (все проходимо)
        self.original_grid = np.zeros((self.height, self.width), dtype=int)
        
        self._update_robot_radius_pixels()
        self.grid = self._expand_obstacles(self.original_grid)
        
        return self.grid
    
    def add_wall_line(self, x1: int, y1: int, x2: int, y2: int):
        """Добавление стены-линии"""
        self.walls.append((x1, y1, x2, y2))
        self._rebuild_grid()
    
    def add_shelf_rect(self, x1: int, y1: int, x2: int, y2: int):
        """Добавление стеллажа-прямоугольника"""
        # Нормализуем координаты
        x1, x2 = min(x1, x2), max(x1, x2)
        y1, y2 = min(y1, y2), max(y1, y2)
        self.shelves.append((x1, y1, x2, y2))
        self._rebuild_grid()
    
    def remove_shelf_at(self, x: int, y: int) -> bool:
        """Удаление стеллажа в указанной точке"""
        for i, (x1, y1, x2, y2) in enumerate(self.shelves):
            if x1 <= x <= x2 and y1 <= y <= y2:
                del self.shelves[i]
                self._rebuild_grid()
                return True
        return False
    
    def clear_markup(self):
        """Очистка разметки"""
        self.walls.clear()
        self.shelves.clear()
        self._rebuild_grid()
    
    def _rebuild_grid(self):
        """Пересоздание сетки на основе разметки"""
        self.original_grid = np.zeros((self.height, self.width), dtype=int)
        
        # Рисуем стены
        for x1, y1, x2, y2 in self.walls:
            self._draw_line_on_grid(x1, y1, x2, y2, 1)
        
        # Рисуем стеллажи
        for x1, y1, x2, y2 in self.shelves:
            self.original_grid[y1:y2+1, x1:x2+1] = 1
        
        # Пересчитываем с учетом радиуса робота
        self.grid = self._expand_obstacles(self.original_grid)
    
    def _draw_line_on_grid(self, x1: int, y1: int, x2: int, y2: int, value: int):
        """Рисование линии на сетке (алгоритм Брезенхема)"""
        dx = abs(x2 - x1)
        dy = abs(y2 - y1)
        sx = 1 if x1 < x2 else -1
        sy = 1 if y1 < y2 else -1
        err = dx - dy
        
        x, y = x1, y1
        while True:
            if 0 <= x < self.width and 0 <= y < self.height:
                self.original_grid[y, x] = value
            
            if x == x2 and y == y2:
                break
                
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x += sx
            if e2 < dx:
                err += dx
                y += sy
    
    def save_markup(self, filepath: str):
        """Сохранение разметки"""
        data = {
            "walls": self.walls,
            "shelves": self.shelves,
            "scale": self.scale,
            "robot_radius_meters": self.robot_radius_meters
        }
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
    
    def load_markup(self, filepath: str):
        """Загрузка разметки"""
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            self.walls = data.get("walls", [])
            self.shelves = data.get("shelves", [])
            self.scale = data.get("scale", 0.1)
            self.robot_radius_meters = data.get("robot_radius_meters", 0.3)
            
            self._update_robot_radius_pixels()
            self._rebuild_grid()
            return True
        except:
            return False
    
    def get_markup_image(self) -> Image.Image:
        """Получение изображения с разметкой"""
        if self.original_image is None:
            return None
        
        img = self.original_image.copy()
        draw = ImageDraw.Draw(img)
        
        # Рисуем стены
        for x1, y1, x2, y2 in self.walls:
            draw.line([x1, y1, x2, y2], fill="red", width=3)
        
        # Рисуем стеллажи
        for x1, y1, x2, y2 in self.shelves:
            draw.rectangle([x1, y1, x2, y2], outline="blue", fill=None, width=2)
        
        return img
    
    def _expand_obstacles(self, grid: np.ndarray) -> np.ndarray:
        """Расширение препятствий на радиус робота"""
        if self.robot_radius_pixels <= 1:
            return grid
        
        expanded = grid.copy()
        r = self.robot_radius_pixels
        
        obstacles = np.where(grid == 1)
        for y, x in zip(obstacles[0], obstacles[1]):
            y_min = max(0, y - r)
            y_max = min(self.height, y + r + 1)
            x_min = max(0, x - r)
            x_max = min(self.width, x + r + 1)
            expanded[y_min:y_max, x_min:x_max] = 1
        
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
        if hasattr(self, 'original_grid'):
            self.grid = self._expand_obstacles(self.original_grid)
    
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
        
        if self.grid[y, x] == 1:
            return False
        
        if not check_radius:
            return True
        
        r = self.robot_radius_pixels
        for dx in [-r, 0, r]:
            for dy in [-r, 0, r]:
                nx, ny = x + dx, y + dy
                if 0 <= nx < self.width and 0 <= ny < self.height:
                    if self.grid[ny, nx] == 1:
                        return False
        return True
    
    def is_shelf(self, x: int, y: int) -> bool:
        """Проверка, является ли точка стеллажом"""
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.original_grid[y, x] == 1
        return False
    
    def find_nearest_walkable(self, x: int, y: int, max_radius: int = 50) -> Optional[Tuple[int, int]]:
        """Поиск ближайшей проходимой точки"""
        if self.is_walkable(x, y, check_radius=False):
            return (x, y)
        
        for r in range(1, max_radius):
            candidates = []
            for dx in range(-r, r + 1):
                for dy in range(-r, r + 1):
                    if abs(dx) == r or abs(dy) == r:
                        nx, ny = x + dx, y + dy
                        if self.is_walkable(nx, ny, check_radius=False):
                            dist = (dx * dx + dy * dy) ** 0.5
                            candidates.append((dist, nx, ny))
            
            if candidates:
                candidates.sort()
                return (candidates[0][1], candidates[0][2])
        
        return None
    
    # Остальные методы (A*, оптимизация маршрутов и т.д.) остаются без изменений
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
        """Алгоритм A* для поиска пути"""
        start_walkable = self.is_walkable(*start, check_radius=False)
        goal_walkable = self.is_walkable(*goal, check_radius=False)
        
        if not start_walkable or not goal_walkable:
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
                path = []
                while current in came_from:
                    path.append(current)
                    current = came_from[current]
                path.append(start)
                return path[::-1]
            
            for dx, dy in directions:
                neighbor = (current[0] + dx, current[1] + dy)
                
                if not self.is_walkable(*neighbor, check_radius=False):
                    continue
                
                tentative_g = g_score[current] + 1
                
                if neighbor not in g_score or tentative_g < g_score[neighbor]:
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g
                    f_score = tentative_g + heuristic(neighbor, goal)
                    heapq.heappush(open_set, (f_score, neighbor))
        
        return None
    
    def compute_distance_matrix(self, points: List[Tuple[int, int]], 
                               start: Tuple[int, int], 
                               end: Tuple[int, int]) -> dict:
        """Предварительный расчет матрицы расстояний между всеми точками"""
        n = len(points)
        distances = {}
        
        for i, point in enumerate(points):
            path = self.a_star(start, point)
            dist = len(path) - 1 if path else float('inf')
            distances[('start', i)] = dist
        
        for i in range(n):
            for j in range(i + 1, n):
                path = self.a_star(points[i], points[j])
                dist = len(path) - 1 if path else float('inf')
                distances[(i, j)] = dist
                distances[(j, i)] = dist
        
        for i, point in enumerate(points):
            path = self.a_star(point, end)
            dist = len(path) - 1 if path else float('inf')
            distances[(i, 'end')] = dist
        
        return distances
    
    def find_optimal_route_simple(self, start: Tuple[int, int], 
                                 points: List[Tuple[int, int]], 
                                 end: Tuple[int, int]) -> Tuple[List[Tuple[int, int]], float, List[int]]:
        """Упрощенный поиск оптимального маршрута"""
        from itertools import permutations
        
        n = len(points)
        if n == 0:
            path = self.a_star(start, end)
            if path:
                return path, (len(path) - 1) * self.scale, []
            return [], float('inf'), []
        
        if n > 7:
            return self.find_greedy_route(start, points, end)
        
        distances = self.compute_distance_matrix(points, start, end)
        
        invalid_points = []
        for i, point in enumerate(points):
            if distances[('start', i)] == float('inf'):
                invalid_points.append(i)
            if distances[(i, 'end')] == float('inf'):
                invalid_points.append(i)
        
        if invalid_points:
            return [], float('inf'), []
        
        best_distance = float('inf')
        best_order = None
        
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
            return [], float('inf'), []
        
        full_path = []
        
        path = self.a_star(start, points[best_order[0]])
        if path:
            full_path.extend(path[:-1])
        else:
            return [], float('inf'), []
        
        for i in range(len(best_order) - 1):
            path = self.a_star(points[best_order[i]], points[best_order[i + 1]])
            if path:
                full_path.extend(path[:-1])
            else:
                return [], float('inf'), []
        
        path = self.a_star(points[best_order[-1]], end)
        if path:
            full_path.extend(path)
        else:
            return [], float('inf'), []
        
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
            
            if best_path:
                if full_path:
                    full_path.extend(best_path[:-1])
                else:
                    full_path.extend(best_path[:-1])
                total_distance += best_dist
            
            order.append(best_next)
            unvisited.remove(best_next)
            current_pos = points[best_next]
        
        path = self.a_star(current_pos, end)
        if path:
            full_path.extend(path)
            total_distance += len(path) - 1
        else:
            return [], float('inf'), []
        
        return full_path, total_distance * self.scale, order