import numpy as np
from PIL import Image
import heapq
from typing import List, Tuple, Optional

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
        self.grid = (img_array < 128).astype(int)  # черный = препятствие
        
        # Пересчет радиуса робота в пиксели
        self._update_robot_radius_pixels()
        
        return self.grid
    
    def set_scale(self, pixel_distance: float, real_distance: float):
        """Установка масштаба карты"""
        if pixel_distance > 0:
            self.scale = real_distance / pixel_distance
            self._update_robot_radius_pixels()
    
    def set_robot_radius_meters(self, radius_meters: float):
        """Установка радиуса робота в метрах"""
        self.robot_radius_meters = radius_meters
        self._update_robot_radius_pixels()
    
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
        """Проверка, является ли точка стеллажом"""
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.grid[y, x] == 1
        return False
    
    def find_nearest_walkable(self, x: int, y: int, max_radius: int = 50) -> Optional[Tuple[int, int]]:
        """Поиск ближайшей проходимой точки (увеличен радиус)"""
        # Если точка уже проходима
        if self.is_walkable(x, y, check_radius=False):
            return (x, y)
        
        # Поиск по спирали от точки
        for r in range(1, max_radius):
            # Проверяем точки на расстоянии r
            for dx in range(-r, r + 1):
                for dy in [-r, r]:  # Только верх и низ
                    nx, ny = x + dx, y + dy
                    if self.is_walkable(nx, ny, check_radius=False):
                        return (nx, ny)
            
            for dy in range(-r + 1, r):  # Левая и правая стороны (без углов)
                for dx in [-r, r]:
                    nx, ny = x + dx, y + dy
                    if self.is_walkable(nx, ny, check_radius=False):
                        return (nx, ny)
        
        return None
    
    def a_star(self, start: Tuple[int, int], goal: Tuple[int, int]) -> Optional[List[Tuple[int, int]]]:
        """Алгоритм A* для поиска пути (исправлено)"""
        # Используем менее строгую проверку для точек старта и финиша
        if not self.is_walkable(*start, check_radius=False) or not self.is_walkable(*goal, check_radius=False):
            return None
        
        def heuristic(a, b):
            return abs(a[0] - b[0]) + abs(a[1] - b[1])
        
        open_set = []
        heapq.heappush(open_set, (0, start))
        came_from = {}
        g_score = {start: 0}
        
        directions = [(0, 1), (1, 0), (0, -1), (-1, 0)]
        
        # Ограничение итераций для предотвращения зависания
        max_iterations = self.width * self.height // 4
        iterations = 0
        
        while open_set and iterations < max_iterations:
            iterations += 1
            current = heapq.heappop(open_set)[1]
            
            if current == goal:
                # Восстановление пути
                path = []
                while current in came_from:
                    path.append(current)
                    current = came_from[current]
                path.append(start)
                return path[::-1]
            
            for dx, dy in directions:
                neighbor = (current[0] + dx, current[1] + dy)
                
                # Используем менее строгую проверку для промежуточных точек
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
        
        # От старта ко всем точкам
        for i, point in enumerate(points):
            path = self.a_star(start, point)
            distances[('start', i)] = len(path) - 1 if path else float('inf')
        
        # Между всеми точками (только уникальные пары)
        for i in range(n):
            for j in range(i + 1, n):
                path = self.a_star(points[i], points[j])
                dist = len(path) - 1 if path else float('inf')
                distances[(i, j)] = dist
                distances[(j, i)] = dist  # Симметричность
        
        # От всех точек к финишу
        for i, point in enumerate(points):
            path = self.a_star(point, end)
            distances[(i, 'end')] = len(path) - 1 if path else float('inf')
        
        return distances
    
    def find_optimal_route_simple(self, start: Tuple[int, int], 
                                 points: List[Tuple[int, int]], 
                                 end: Tuple[int, int]) -> Tuple[List[Tuple[int, int]], float, List[int]]:
        """Упрощенный поиск оптимального маршрута для небольшого количества точек"""
        from itertools import permutations
        
        n = len(points)
        if n == 0:
            path = self.a_star(start, end)
            if path:
                return path, (len(path) - 1) * self.scale, []
            return [], float('inf'), []
        
        if n > 7:
            # Для большого количества точек используем жадный алгоритм
            return self.find_greedy_route(start, points, end)
        
        # Вычисляем матрицу расстояний
        distances = self.compute_distance_matrix(points, start, end)
        
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
            return [], float('inf'), []
        
        # Восстанавливаем полный путь
        full_path = []
        
        path = self.a_star(start, points[best_order[0]])
        if path:
            full_path.extend(path[:-1])
        
        for i in range(len(best_order) - 1):
            path = self.a_star(points[best_order[i]], points[best_order[i + 1]])
            if path:
                full_path.extend(path[:-1])
        
        path = self.a_star(points[best_order[-1]], end)
        if path:
            full_path.extend(path)
        
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