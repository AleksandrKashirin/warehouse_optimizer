import json
import math
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk
from typing import List

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageTk

from map_processor import MapProcessor
from route_optimizer import RouteOptimizer


class WarehouseGUI:
    def __init__(self, root):
        self.root = root
        self.map_processor = MapProcessor()
        self.route_optimizer = RouteOptimizer()

        self.canvas = None
        self.photo_image = None
        self.map_image = None
        self.scale_points = []
        self.start_point = None
        self.end_point = None
        self.mode = "view"
        self.scale_set = False
        self.robot_radius_set = False
        
        # Для рисования стен
        self.current_wall_chain = []
        self.temp_line_start = None
        
        # Для рисования стеллажей
        self.temp_rect_start = None

        self.setup_ui()

        self.optimized_samples = None

        self.auto_load_last_config()

        # Для масштабирования карты
        self.zoom_factor = 1.0
        self.min_zoom = 0.1
        self.max_zoom = 5.0

    def setup_ui(self):
        # Панель управления - первая строка
        control_frame1 = tk.Frame(self.root)
        control_frame1.pack(side=tk.TOP, fill=tk.X, padx=5, pady=2)

        tk.Button(control_frame1, text="Загрузить карту", command=self.load_map).pack(side=tk.LEFT, padx=2)
        tk.Button(control_frame1, text="Загрузить товары", command=self.load_products).pack(side=tk.LEFT, padx=2)
        tk.Button(control_frame1, text="Установить масштаб", command=self.set_scale_mode).pack(side=tk.LEFT, padx=2)
        tk.Button(control_frame1, text="Радиус робота", command=self.set_robot_radius).pack(side=tk.LEFT, padx=2)
        tk.Button(control_frame1, text="Разместить товары", command=self.place_products_mode).pack(side=tk.LEFT, padx=2)

        # Панель управления - вторая строка
        control_frame2 = tk.Frame(self.root)
        control_frame2.pack(side=tk.TOP, fill=tk.X, padx=5, pady=2)

        tk.Button(control_frame2, text="Рисовать стены", command=self.draw_walls_mode).pack(side=tk.LEFT, padx=2)
        tk.Button(control_frame2, text="Рисовать стеллажи", command=self.draw_shelves_mode).pack(side=tk.LEFT, padx=2)
        tk.Button(control_frame2, text="Удалить стеллаж", command=self.remove_shelf_mode).pack(side=tk.LEFT, padx=2)
        tk.Button(control_frame2, text="Очистить разметку", command=self.clear_markup).pack(side=tk.LEFT, padx=2)
        tk.Button(control_frame2, text="Сохранить разметку", command=self.save_markup).pack(side=tk.LEFT, padx=2)
        tk.Button(control_frame2, text="Загрузить разметку", command=self.load_markup).pack(side=tk.LEFT, padx=2)

        # Панель управления - третья строка
        control_frame3 = tk.Frame(self.root)
        control_frame3.pack(side=tk.TOP, fill=tk.X, padx=5, pady=2)

        tk.Button(control_frame3, text="Установить старт/финиш", command=self.set_route_points_mode).pack(side=tk.LEFT, padx=2)
        tk.Button(control_frame3, text="Генерировать маршруты", command=self.generate_routes).pack(side=tk.LEFT, padx=2)
        
        # НОВАЯ КНОПКА для генерации с ограничениями
        self.generate_limited_btn = tk.Button(control_frame3, text="Генерировать с ограничениями", 
                                            command=self.generate_routes_with_limits, bg="lightblue")
        self.generate_limited_btn.pack(side=tk.LEFT, padx=2)
        
        tk.Button(control_frame3, text="Сохранить товары", command=self.save_products).pack(side=tk.LEFT, padx=2)
        tk.Button(control_frame3, text="Просмотр маршрутов", command=self.view_routes).pack(side=tk.LEFT, padx=2)

        # Информационная панель
        info_frame = tk.Frame(self.root)
        info_frame.pack(side=tk.TOP, fill=tk.X, padx=5)

        self.info_label = tk.Label(info_frame, text="Загрузите карту склада", anchor=tk.W)
        self.info_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Статус панель
        self.status_label = tk.Label(info_frame, text="", anchor=tk.E, fg="blue")
        self.status_label.pack(side=tk.RIGHT, padx=10)

        # Холст для отображения карты
        canvas_frame = tk.Frame(self.root)
        canvas_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.canvas = tk.Canvas(canvas_frame, bg="gray", width=800, height=600)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Скроллбары
        v_scrollbar = tk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        h_scrollbar = tk.Scrollbar(self.root, orient=tk.HORIZONTAL, command=self.canvas.xview)
        h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)

        self.canvas.config(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        self.canvas.bind("<Button-1>", self.on_canvas_click)
        self.canvas.bind("<Motion>", self.on_mouse_move)
        # Привязка событий колеса мыши
        self.canvas.bind("<MouseWheel>", self.on_mousewheel)  # Windows
        self.canvas.bind("<Button-4>", self.on_mousewheel)    # Linux scroll up
        self.canvas.bind("<Button-5>", self.on_mousewheel)    # Linux scroll down
        
        # Привязка клавиш
        self.root.bind("<KeyPress>", self.on_key_press)
        self.root.focus_set()

        self.update_status()
    
    def on_key_press(self, event):
        """Обработка нажатий клавиш"""
        if event.keysym == "Escape":
            if self.mode == "draw_walls" and self.current_wall_chain:
                # Сохраняем текущую цепочку стен
                self.save_wall_chain()
                self.info_label.config(text="Цепочка стен сохранена. Нажмите для начала новой цепочки")
    
    def on_mousewheel(self, event):
        """Обработка колеса мыши для навигации и масштабирования"""
        # Определяем направление прокрутки
        if event.num == 4 or event.delta > 0:
            delta = 1  # вверх
        elif event.num == 5 or event.delta < 0:
            delta = -1  # вниз
        else:
            return

        # Ctrl + колесо = масштабирование
        if event.state & 0x4:  # Ctrl pressed
            old_zoom = self.zoom_factor
            if delta > 0:
                self.zoom_factor = min(self.max_zoom, self.zoom_factor * 1.2)
            else:
                self.zoom_factor = max(self.min_zoom, self.zoom_factor / 1.2)
            
            if self.zoom_factor != old_zoom:
                # Получаем позицию курсора на канвасе
                canvas_x = self.canvas.canvasx(event.x)
                canvas_y = self.canvas.canvasy(event.y)
                
                self.display_map()
                
                # Центрируем вид на точке курсора
                self.canvas.scan_mark(int(event.x), int(event.y))
                self.canvas.scan_dragto(int(event.x), int(event.y), gain=1)
        
        # Shift + колесо = горизонтальная прокрутка
        elif event.state & 0x1:  # Shift pressed
            self.canvas.xview_scroll(-delta * 3, "units")
        
        # Обычная прокрутка по вертикали
        else:
            self.canvas.yview_scroll(-delta * 3, "units")

    def draw_walls_mode(self):
        """Режим рисования стен"""
        self.mode = "draw_walls"
        self.current_wall_chain = []
        self.temp_line_start = None
        self.info_label.config(text="Режим рисования стен. Кликайте для соединения точек. ESC - сохранить цепочку")
    
    def draw_shelves_mode(self):
        """Режим рисования стеллажей"""
        self.mode = "draw_shelves"
        self.temp_rect_start = None
        self.info_label.config(text="Режим рисования стеллажей. Кликните две точки для создания прямоугольника")
    
    def remove_shelf_mode(self):
        """Режим удаления стеллажей"""
        self.mode = "remove_shelf"
        self.info_label.config(text="Режим удаления стеллажей. Кликните на стеллаж (синий прямоугольник) для удаления")
    
    def save_wall_chain(self):
        """Сохранение текущей цепочки стен"""
        if len(self.current_wall_chain) > 1:
            for i in range(len(self.current_wall_chain) - 1):
                x1, y1 = self.current_wall_chain[i]
                x2, y2 = self.current_wall_chain[i + 1]
                self.map_processor.add_wall_line(int(x1), int(y1), int(x2), int(y2))
        
        self.current_wall_chain = []
        self.temp_line_start = None
        self.display_map()
    
    def clear_markup(self):
        """Очистка разметки"""
        if messagebox.askyesno("Подтверждение", "Очистить всю разметку (стены и стеллажи)?"):
            self.map_processor.clear_markup()
            self.display_map()
            self.info_label.config(text="Разметка очищена")
    
    def save_markup(self):
        """Сохранение разметки"""
        filepath = filedialog.asksaveasfilename(
            title="Сохранить разметку",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if filepath:
            self.map_processor.save_markup(filepath)
            messagebox.showinfo("Успех", "Разметка сохранена")
    
    def load_markup(self):
        """Загрузка разметки"""
        filepath = filedialog.askopenfilename(
            title="Загрузить разметку",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if filepath:
            if self.map_processor.load_markup(filepath):
                self.current_markup_path = filepath
                self.scale_set = True
                self.robot_radius_set = True
                self.update_status()
                self.display_map()
                messagebox.showinfo("Успех", "Разметка загружена")
                self.save_current_config()
            else:
                messagebox.showerror("Ошибка", "Не удалось загрузить разметку")

    def load_map(self):
        filepath = filedialog.askopenfilename(
            title="Выберите карту склада",
            filetypes=[
                ("Image files", "*.png *.jpg *.jpeg *.bmp"),
                ("PNG files", "*.png"),
                ("JPEG files", "*.jpg *.jpeg"),
                ("BMP files", "*.bmp"),
                ("All files", "*.*")
            ],
        )
        if filepath:
            try:
                self.current_map_path = filepath
                
                # Загружаем карту
                grid = self.map_processor.load_map(filepath)
                
                self.display_map()
                self.update_status()
                
                self.info_label.config(
                    text=f"Карта загружена: {self.map_processor.width}x{self.map_processor.height} пикселей"
                )
                self.save_current_config()
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось загрузить карту: {e}")

    def export_csv(self):
        """Экспорт всех маршрутов в CSV"""
        try:
            count = self.route_optimizer.export_routes_to_csv()
            messagebox.showinfo("Успех", f"Экспортировано {count} маршрутов в output/routes/routes_summary.csv")
        except ValueError as e:
            messagebox.showwarning("Внимание", str(e))
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка экспорта: {e}")

    def update_status(self):
        """Обновление статусной строки"""
        status_parts = []

        if self.scale_set:
            status_parts.append(f"Масштаб: 1px = {self.map_processor.scale:.2f}м")
        else:
            status_parts.append("Масштаб: не задан")

        if self.robot_radius_set:
            status_parts.append(f"Радиус робота: {self.map_processor.robot_radius_meters:.2f}м")
        else:
            status_parts.append("Радиус: не задан")

        # Добавляем информацию о наличии данных о количестве
        if self.route_optimizer.has_amount_data():
            status_parts.append("Количества: есть")
            self.generate_limited_btn.config(state="normal")
        else:
            status_parts.append("Количества: нет")
            self.generate_limited_btn.config(state="disabled")

        self.status_label.config(text=" | ".join(status_parts))

    def set_robot_radius(self):
        """Установка радиуса робота в метрах"""
        current = self.map_processor.robot_radius_meters
        radius = simpledialog.askfloat(
            "Радиус робота",
            f"Введите радиус робота в МЕТРАХ\n(текущий: {current:.2f} м):",
            initialvalue=current,
            minvalue=0.1,
            maxvalue=2.0,
        )
        if radius:
            self.map_processor.set_robot_radius_meters(radius)
            self.robot_radius_set = True
            self.update_status()
            self.info_label.config(
                text=f"Радиус робота: {radius:.2f} м ({self.map_processor.robot_radius_pixels} пикселей)"
            )
            self.display_map()

    def set_scale_mode(self):
        self.mode = "scale"
        self.scale_points = []
        self.canvas.delete("scale")
        self.info_label.config(text="Кликните на две точки с известным расстоянием")

    def place_products_mode(self):
        if self.map_processor.grid is None:
            messagebox.showwarning("Предупреждение", "Сначала загрузите карту склада")
            return
        if not self.route_optimizer.products:
            messagebox.showwarning("Предупреждение", "Сначала загрузите товары")
            return
        self.mode = "place"
        self.show_product_selector()

    def show_product_selector(self):
        selector = tk.Toplevel(self.root)
        selector.title("Выберите товар для размещения")

        placed_count = len(self.route_optimizer.placed_products)
        access_count = len(self.route_optimizer.access_points)
        total_count = len(self.route_optimizer.products)
        
        # Подсчет товаров с количеством > 0
        with_amount = sum(1 for p in self.route_optimizer.products.values() if p.amount > 0)
        total_amount = sum(p.amount for p in self.route_optimizer.products.values())

        info_frame = tk.Frame(selector)
        info_frame.pack(padx=10, pady=5)
        
        info_text = f"Размещено: {placed_count}/{total_count} товаров, доступно: {access_count}"
        if self.route_optimizer.has_amount_data():
            info_text += f", с количеством: {with_amount}, общее количество: {total_amount}"
        
        tk.Label(
            info_frame,
            text=info_text,
            font=("Arial", 10, "bold"),
        ).pack()
        
        if access_count < 5:
            tk.Label(
                info_frame, text=f"Минимум для маршрутов: 5 товаров с доступом", fg="red"
            ).pack()
            
        tk.Label(
            info_frame,
            text="Кликайте на СТЕЛЛАЖИ (синие прямоугольники) или рядом с ними",
            fg="blue",
        ).pack()

        listbox = tk.Listbox(selector, width=80, height=20)
        listbox.pack(padx=10, pady=10)

        for product in self.route_optimizer.products.values():
            status = "✓" if product.id in self.route_optimizer.access_points else ("◐" if product.x >= 0 else "✗")
            amount_info = f" (кол-во: {product.amount})" if product.amount > 0 else ""
            listbox.insert(tk.END, f"{status} {product.id}: {product.name}{amount_info}")

        def on_select():
            selection = listbox.curselection()
            if selection:
                index = selection[0]
                product = list(self.route_optimizer.products.values())[index]
                self.selected_product_id = product.id
                self.info_label.config(
                    text=f"Кликните на СТЕЛЛАЖ для размещения: {product.name}"
                )
                selector.destroy()

        def on_cancel():
            self.mode = "view"
            self.update_info_after_placement()
            selector.destroy()

        button_frame = tk.Frame(selector)
        button_frame.pack(pady=5)
        tk.Button(button_frame, text="Выбрать", command=on_select).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Завершить", command=on_cancel).pack(side=tk.LEFT, padx=5)

    def update_info_after_placement(self):
        """Обновление информации после размещения товаров"""
        placed_count = len(self.route_optimizer.placed_products)
        access_count = len(self.route_optimizer.access_points)
        total_count = len(self.route_optimizer.products)
        
        info_text = f"Размещено товаров: {placed_count}/{total_count}, доступно: {access_count}"
        if self.route_optimizer.has_amount_data():
            with_amount = sum(1 for p in self.route_optimizer.products.values() if p.amount > 0)
            info_text += f", с количеством: {with_amount}"
            
        self.info_label.config(text=info_text)

    def set_route_points_mode(self):
        self.mode = "route_points"
        self.start_point = None
        self.end_point = None
        self.canvas.delete("route_point")
        self.display_map()
        self.info_label.config(
            text="Кликните в ПРОХОДЕ (белая область) для установки точки СТАРТА"
        )

    def load_products(self):
        filepath = filedialog.askopenfilename(
            title="Выберите файл с товарами",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
        )
        if filepath:
            try:
                self.current_products_path = filepath
                self.route_optimizer.load_products(filepath)
                self.display_map()
                self.update_status()  # Важно обновить статус после загрузки
                
                count = len(self.route_optimizer.products)
                placed = len(self.route_optimizer.placed_products)
                access_count = len(self.route_optimizer.access_points)
                
                info_text = f"Загружено товаров: {count}, размещено: {placed}, с доступом: {access_count}"
                if self.route_optimizer.has_amount_data():
                    with_amount = sum(1 for p in self.route_optimizer.products.values() if p.amount > 0)
                    total_amount = sum(p.amount for p in self.route_optimizer.products.values())
                    info_text += f", с количеством: {with_amount}, общее количество: {total_amount}"
                    
                self.info_label.config(text=info_text)
                self.save_current_config() 
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось загрузить товары: {e}")

    def save_products(self):
        filepath = filedialog.asksaveasfilename(
            title="Сохранить товары",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
        )
        if filepath:
            try:
                self.route_optimizer.save_products(filepath)
                messagebox.showinfo("Успех", "Товары сохранены")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось сохранить: {e}")

    def on_canvas_click(self, event):
        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)

        if self.mode == "scale":
            self.scale_points.append((x, y))
            self.canvas.create_oval(x - 3, y - 3, x + 3, y + 3, fill="red", tags="scale")

            if len(self.scale_points) == 2:
                pixel_dist = math.sqrt(
                    (self.scale_points[1][0] - self.scale_points[0][0]) ** 2
                    + (self.scale_points[1][1] - self.scale_points[0][1]) ** 2
                )
                real_dist = simpledialog.askfloat(
                    "Масштаб", "Введите реальное расстояние в МЕТРАХ:"
                )
                if real_dist:
                    self.map_processor.set_scale(pixel_dist, real_dist)
                    self.scale_set = True
                    self.update_status()
                    self.info_label.config(
                        text=f"Масштаб установлен: 1 пиксель = {self.map_processor.scale:.3f} м"
                    )
                        
                self.canvas.delete("scale")
                self.mode = "view"

        elif self.mode == "draw_walls":
            ix, iy = int(x), int(y)
            
            if not self.temp_line_start:
                # Начинаем новую линию
                self.temp_line_start = (ix, iy)
                self.current_wall_chain.append((ix, iy))
                self.canvas.create_oval(ix - 2, iy - 2, ix + 2, iy + 2, fill="red", tags="temp_wall")
            else:
                # Заканчиваем линию
                self.current_wall_chain.append((ix, iy))
                
                # Рисуем линию
                self.canvas.create_line(
                    self.temp_line_start[0], self.temp_line_start[1], 
                    ix, iy, 
                    fill="red", width=2, tags="temp_wall"
                )
                self.canvas.create_oval(ix - 2, iy - 2, ix + 2, iy + 2, fill="red", tags="temp_wall")
                
                # Проверяем замыкание (клик рядом с первой точкой)
                if len(self.current_wall_chain) > 2:
                    first_point = self.current_wall_chain[0]
                    dist = math.sqrt((ix - first_point[0])**2 + (iy - first_point[1])**2)
                    if dist < 10:  # Замыкаем если близко к первой точке
                        self.current_wall_chain.append(first_point)
                        self.canvas.create_line(
                            ix, iy, first_point[0], first_point[1],
                            fill="red", width=2, tags="temp_wall"
                        )
                        self.save_wall_chain()
                        self.canvas.delete("temp_wall")
                        self.info_label.config(text="Многоугольник замкнут и сохранен")
                        return
                
                self.temp_line_start = (ix, iy)

        elif self.mode == "draw_shelves":
            ix, iy = int(x), int(y)
            
            if not self.temp_rect_start:
                # Начинаем прямоугольник
                self.temp_rect_start = (ix, iy)
                self.canvas.create_oval(ix - 2, iy - 2, ix + 2, iy + 2, fill="blue", tags="temp_shelf")
                self.info_label.config(text="Кликните вторую точку для завершения прямоугольника")
            else:
                # Заканчиваем прямоугольник
                x1, y1 = self.temp_rect_start
                x2, y2 = ix, iy
                
                self.map_processor.add_shelf_rect(x1, y1, x2, y2)
                self.display_map()
                
                self.temp_rect_start = None
                self.canvas.delete("temp_shelf")
                self.info_label.config(text="Стеллаж добавлен. Кликните для следующего")

        elif self.mode == "remove_shelf":
            ix, iy = int(x), int(y)
            
            if self.map_processor.remove_shelf_at(ix, iy):
                self.display_map()
                self.info_label.config(text="Стеллаж удален. Кликните на другой стеллаж для удаления")
            else:
                self.info_label.config(text="Стеллаж не найден. Кликните точно на синий прямоугольник")

        elif self.mode == "place" and hasattr(self, "selected_product_id"):
            ix, iy = int(x), int(y)
            
            # Рассчитываем адекватный радиус поиска (минимум в 3 раза больше радиуса робота)
            search_radius = max(50, self.map_processor.robot_radius_pixels * 3)

            if self.map_processor.is_shelf(ix, iy):
                access = self.map_processor.find_nearest_walkable(ix, iy, max_radius=search_radius)
                if access:
                    self.route_optimizer.place_product(self.selected_product_id, ix, iy, access)
                    self.display_map()
                    self.info_label.config(text=f"Товар размещен на стеллаже с точкой доступа")
                    self.show_product_selector()
                else:
                    scale_info = f"масштаб: 1px = {self.map_processor.scale:.3f}м"
                    search_radius_m = search_radius * self.map_processor.scale
                    robot_radius_info = f"радиус робота: {self.map_processor.robot_radius_pixels}px = {self.map_processor.robot_radius_meters:.2f}м"
                    
                    error_msg = (f"К этому месту нет доступа!\n\n"
                                f"Позиция: ({ix}, {iy})\n"
                                f"Поиск в радиусе: {search_radius}px = {search_radius_m:.2f}м\n"
                                f"{scale_info}\n"
                                f"{robot_radius_info}")
                    
                    messagebox.showwarning("Диагностика доступа", error_msg)
            else:
                found = False
                for r in range(1, search_radius):
                    for dx in range(-r, r + 1):
                        for dy in range(-r, r + 1):
                            sx, sy = ix + dx, iy + dy
                            if self.map_processor.is_shelf(sx, sy):
                                access = self.map_processor.find_nearest_walkable(sx, sy, max_radius=search_radius)
                                if access:
                                    self.route_optimizer.place_product(self.selected_product_id, sx, sy, access)
                                    self.display_map()
                                    self.info_label.config(text=f"Товар размещен на ближайшем стеллаже с точкой доступа")
                                    self.show_product_selector()
                                    found = True
                                    break
                        if found:
                            break
                    if found:
                        break

                if not found:
                    messagebox.showwarning("Внимание", "Кликните ближе к стеллажу (синий прямоугольник)")

        elif self.mode == "route_points":
            ix, iy = int(x), int(y)

            if not self.start_point:
                if self.map_processor.is_walkable(ix, iy, check_radius=False):
                    self.start_point = (ix, iy)
                    self.display_map()
                    self.info_label.config(
                        text="Кликните в ПРОХОДЕ для установки точки ФИНИША"
                    )
                else:
                    nearest = self.map_processor.find_nearest_walkable(ix, iy, max_radius=10)
                    if nearest:
                        self.start_point = nearest
                        self.display_map()
                        self.info_label.config(
                            text="Кликните в ПРОХОДЕ для установки точки ФИНИША"
                        )
                    else:
                        messagebox.showwarning(
                            "Внимание",
                            "Точка старта должна быть в проходе (белая область)!",
                        )

            elif not self.end_point:
                if self.map_processor.is_walkable(ix, iy, check_radius=False):
                    self.end_point = (ix, iy)
                    self.display_map()
                    self.info_label.config(
                        text=f"Старт: {self.start_point}, Финиш: {self.end_point}"
                    )
                    self.mode = "view"
                    self.save_current_config()
                else:
                    nearest = self.map_processor.find_nearest_walkable(ix, iy, max_radius=10)
                    if nearest:
                        self.end_point = nearest
                        self.display_map()
                        self.info_label.config(
                            text=f"Старт: {self.start_point}, Финиш: {self.end_point}"
                        )
                        self.mode = "view"
                        self.save_current_config()
                    else:
                        messagebox.showwarning(
                            "Внимание",
                            "Точка финиша должна быть в проходе (белая область)!",
                        )

    def on_mouse_move(self, event):
        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)
        ix, iy = int(x), int(y)

        if 0 <= ix < self.map_processor.width and 0 <= iy < self.map_processor.height:
            if self.mode == "view":
                product = self.route_optimizer.get_product_at(ix, iy)
                if product:
                    access_status = "с доступом" if product.id in self.route_optimizer.access_points else "без доступа"
                    amount_info = f", количество: {product.amount}" if product.amount > 0 else ""
                    self.info_label.config(text=f"Товар: {product.id} - {product.name} ({access_status}{amount_info})")
                else:
                    status = (
                        "стеллаж" if self.map_processor.is_shelf(ix, iy) else "проход"
                    )
                    walkable = (
                        "доступно"
                        if self.map_processor.is_walkable(ix, iy, check_radius=False)
                        else "недоступно"
                    )
                    self.info_label.config(text=f"({ix}, {iy}) - {status}, {walkable}")
            elif self.mode == "remove_shelf":
                if self.map_processor.is_shelf(ix, iy):
                    self.info_label.config(text=f"({ix}, {iy}) - стеллаж (кликните для удаления)")
                else:
                    self.info_label.config(text=f"({ix}, {iy}) - не стеллаж")

    def display_map(self):
        if self.map_processor.original_image is None:
            return

        # Получаем изображение с разметкой
        img = self.map_processor.get_markup_image()
        if img is None:
            return

        draw = ImageDraw.Draw(img)

        # Отрисовка размещенных товаров
        for product_id, (x, y) in self.route_optimizer.placed_products.items():
            if product_id in self.route_optimizer.access_points:
                draw.ellipse([x - 3, y - 3, x + 3, y + 3], fill="yellow", outline="orange")
                access_x, access_y = self.route_optimizer.access_points[product_id]
                draw.ellipse([access_x - 2, access_y - 2, access_x + 2, access_y + 2], fill="lightgreen", outline="green")
                draw.line([x, y, access_x, access_y], fill="lightblue", width=1)
            else:
                draw.ellipse([x - 3, y - 3, x + 3, y + 3], fill="orange", outline="red")
            
            draw.text((x + 5, y - 5), product_id, fill="blue")

        # Отрисовка точек старта и финиша
        if self.start_point:
            x, y = self.start_point
            draw.ellipse(
                [x - 5, y - 5, x + 5, y + 5], fill="green", outline="darkgreen", width=2
            )
            draw.text((x + 7, y - 5), "START", fill="green")

        if self.end_point:
            x, y = self.end_point
            draw.ellipse(
                [x - 5, y - 5, x + 5, y + 5], fill="red", outline="darkred", width=2
            )
            draw.text((x + 7, y - 5), "FINISH", fill="red")

        self.map_image = img

        # Применяем масштабирование если нужно
        if self.zoom_factor != 1.0:
            new_width = int(img.width * self.zoom_factor)
            new_height = int(img.height * self.zoom_factor)
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

        self.photo_image = ImageTk.PhotoImage(img)

        self.canvas.delete("all")
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.photo_image)
        self.canvas.config(scrollregion=self.canvas.bbox("all"))

    def generate_routes(self):
        """Обычная генерация маршрутов (оригинальный функционал)"""
        if not self.scale_set:
            messagebox.showwarning("Предупреждение", "Сначала установите масштаб карты!")
            return

        if not self.robot_radius_set:
            if not messagebox.askyesno(
                "Радиус робота",
                "Радиус робота не задан. Использовать значение по умолчанию (0.3 м)?",
            ):
                return
            self.map_processor.set_robot_radius_meters(0.3)
            self.robot_radius_set = True
            self.update_status()

        if not self.start_point or not self.end_point:
            messagebox.showwarning("Предупреждение", "Установите точки старта и финиша")
            return

        access_count = len(self.route_optimizer.access_points)
        if access_count < 5:
            messagebox.showwarning("Предупреждение", f"Разместите минимум 5 товаров с точками доступа. Сейчас: {access_count}")
            return

        num_samples = simpledialog.askinteger("Генерация", "Количество выборок:", initialvalue=10)
        if not num_samples:
            return

        try:
            samples = self.route_optimizer.generate_samples(num_samples)
            self._process_routes(samples, "обычной генерации")

        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка генерации: {e}")

    def generate_routes_with_limits(self):
        """НОВЫЙ ФУНКЦИОНАЛ: Генерация маршрутов с учетом ограничений по количеству"""
        if not self.route_optimizer.has_amount_data():
            messagebox.showwarning("Предупреждение", "Данные о количестве товаров отсутствуют!")
            return

        if not self.scale_set:
            messagebox.showwarning("Предупреждение", "Сначала установите масштаб карты!")
            return

        if not self.robot_radius_set:
            if not messagebox.askyesno(
                "Радиус робота",
                "Радиус робота не задан. Использовать значение по умолчанию (0.3 м)?",
            ):
                return
            self.map_processor.set_robot_radius_meters(0.3)
            self.robot_radius_set = True
            self.update_status()

        if not self.start_point or not self.end_point:
            messagebox.showwarning("Предупреждение", "Установите точки старта и финиша")
            return

        # Проверяем товары с доступом и количеством
        with_amount_and_access = sum(1 for p in self.route_optimizer.products.values() 
                                if p.amount > 0 and p.id in self.route_optimizer.access_points)
        
        if with_amount_and_access < 5:
            messagebox.showwarning("Предупреждение", 
                                f"Минимум 5 товаров должны иметь доступ и количество > 0. Сейчас: {with_amount_and_access}")
            return

        num_samples = simpledialog.askinteger("Генерация с ограничениями", 
                                            "Количество выборок:", initialvalue=73)
        if not num_samples:
            return

        try:
            # 1. Генерируем выборки с ограничениями
            samples = self.route_optimizer.generate_samples_with_limits(num_samples)
            
            # 2. Оптимизируем порядок выборок
            optimized_samples = self.route_optimizer.optimize_samples_order(samples)
            
            # 3. Анализируем группировку по ночам
            night_groups = self.route_optimizer.group_samples_by_nights(optimized_samples)
            stats = self.route_optimizer.analyze_night_efficiency(night_groups)
            
            # 4. Показываем статистику оптимизации
            usage_stats = self.route_optimizer.get_usage_statistics(optimized_samples)
            print("Статистика использования товаров:")
            for product_id, count in usage_stats.items():
                product = self.route_optimizer.products[product_id]
                print(f"{product_id}: {count}/{product.amount}")
            
            print(f"\nОптимизация по ночам:")
            print(f"Эффективность: {stats['efficiency_score']:.1%}")
            for night_info in stats['nights']:
                print(f"Ночь {night_info['night']}: {night_info['unique_products']} товаров, "
                        f"{night_info['avg_changes_per_experiment']:.1f} смен за эксперимент")

            # 5. Генерируем маршруты в оптимизированном порядке
            self._process_routes(optimized_samples, "генерации с ограничениями и оптимизацией")
            
            # 6. Показываем результаты оптимизации
            self.show_optimization_results(night_groups, stats)

        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка генерации с ограничениями: {e}")

    def _process_routes(self, samples, generation_type):
        """Общий метод для обработки сгенерированных выборок"""
        progress = tk.Toplevel(self.root)
        progress.title("Генерация маршрутов")
        progress_label = tk.Label(progress, text="Инициализация...")
        progress_label.pack(padx=20, pady=10)
        progress_bar = ttk.Progressbar(progress, length=300, mode="determinate", maximum=len(samples))
        progress_bar.pack(padx=20, pady=10)

        successful_routes = 0
        failed_routes = 0

        samples_to_process = self.optimized_samples if self.optimized_samples else samples

        for i, sample in enumerate(samples_to_process):
            progress_label.config(text=f"Обработка маршрута {i+1}/{len(samples)}")
            progress.update()

            coords = self.route_optimizer.get_access_coordinates(sample)

            if len(coords) != len(sample):
                failed_routes += 1
                progress_bar["value"] = i + 1
                progress.update()
                continue

            path, distance, order = self.map_processor.find_optimal_route_simple(
                self.start_point, coords, self.end_point
            )

            if path and len(path) > 0:
                if order:
                    ordered_sample = [sample[idx] for idx in order]
                else:
                    ordered_sample = sample

                self.save_route_image(i + 1, path, ordered_sample, distance)
                self.route_optimizer.save_route_info(i + 1, ordered_sample, distance, path)
                self.save_route_segments(i + 1, ordered_sample, path)
                successful_routes += 1
            else:
                failed_routes += 1

            progress_bar["value"] = i + 1
            progress.update()

        progress.destroy()

        if successful_routes > 0:
            messagebox.showinfo(
                "Успех",
                f"Сгенерировано маршрутов ({generation_type}): {successful_routes}\n"
                f"Не удалось построить: {failed_routes}\n"
                f"Сохранено в: output/routes/",
            )
        else:
            access_count = len(self.route_optimizer.access_points)
            with_amount = sum(1 for p in self.route_optimizer.products.values() 
                            if p.amount > 0 and p.id in self.route_optimizer.access_points)
            messagebox.showwarning(
                "Внимание",
                f"Не удалось построить ни одного маршрута.\n"
                f"Проверьте:\n"
                f"- Точки доступа к товарам (зеленые точки на карте)\n"
                f"- Проходимость между стартом, товарами и финишем\n"
                f"- Размер радиуса робота\n"
                f"- Количество товаров (столбец Amount)\n"
                f"Товаров с доступом: {access_count}, с количеством и доступом: {with_amount}",
            )
    
    def save_route_segments(self, route_id: int, products: List[str], path: List[tuple]):
        """Сохранение детальной информации о сегментах маршрута из существующего пути"""
        if not products or not path:
            return
        
        Path("output/routes").mkdir(parents=True, exist_ok=True)
        
        # Получаем все ключевые точки маршрута
        waypoints = [self.start_point]
        for product_id in products:
            if product_id in self.route_optimizer.access_points:
                waypoints.append(self.route_optimizer.access_points[product_id])
        waypoints.append(self.end_point)
        
        # Находим индексы ключевых точек в пути ПОСЛЕДОВАТЕЛЬНО
        waypoint_indices = [0]  # Начинаем со старта (индекс 0)
        
        for i in range(1, len(waypoints)):
            target_waypoint = waypoints[i]
            start_search_from = waypoint_indices[-1]  # Ищем от последней найденной точки
            
            closest_index = start_search_from
            min_distance = float('inf')
            
            # Ищем ближайшую точку начиная с последней найденной
            for j in range(start_search_from, len(path)):
                path_point = path[j]
                distance = ((path_point[0] - target_waypoint[0])**2 + (path_point[1] - target_waypoint[1])**2)**0.5
                if distance < min_distance:
                    min_distance = distance
                    closest_index = j
                # Если расстояние начинает увеличиваться, значит мы прошли минимум
                elif distance > min_distance + 5:  # Добавляем небольшой порог
                    break
            
            waypoint_indices.append(closest_index)
        
        # Убеждаемся что последняя точка - это конец пути
        waypoint_indices[-1] = len(path) - 1
        
        # Разбиваем путь на сегменты между ключевыми точками
        segments = []
        total_distance_pixels = 0
        
        for i in range(len(waypoint_indices) - 1):
            start_idx = waypoint_indices[i]
            end_idx = waypoint_indices[i + 1]
            
            # Извлекаем участок пути между двумя ключевыми точками
            segment_path = path[start_idx:end_idx + 1]
            
            # Вычисляем длину сегмента
            segment_distance_pixels = 0
            if len(segment_path) > 1:
                for j in range(len(segment_path) - 1):
                    p1 = segment_path[j]
                    p2 = segment_path[j + 1]
                    segment_distance_pixels += ((p2[0] - p1[0])**2 + (p2[1] - p1[1])**2)**0.5
            
            total_distance_pixels += segment_distance_pixels
            
            # Переводим в метры
            segment_distance_meters = segment_distance_pixels * self.map_processor.scale
            
            segment_info = {
                "segment": i + 1,
                "from": f"{'Старт' if i == 0 else f'Товар{i}'}", 
                "to": f"{'Финиш' if i == len(waypoint_indices) - 2 else f'Товар{i+1}'}",
                "distance": round(segment_distance_meters, 2),
                "path_points": len(segment_path),
                "start_index": start_idx,
                "end_index": end_idx
            }
            segments.append(segment_info)
        
        # Общая дистанция в метрах
        total_distance_meters = total_distance_pixels * self.map_processor.scale
        
        print(f"Маршрут {route_id}: {len(segments)} сегментов, общая длина = {total_distance_meters:.2f}м")
        
        path_data = {
            "route_id": route_id,
            "total_segments": len(segments),
            "segments": segments,
            "total_calculated_distance": round(total_distance_meters, 2),
            "waypoints": waypoints,
            "waypoint_indices": waypoint_indices
        }
        
        filepath = f"output/routes/route_{route_id}_path.json"
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(path_data, f, ensure_ascii=False, indent=2)

    def save_route_image(self, route_id: int, path: List[tuple], products: List[str], distance: float):
        if not self.map_image:
            return

        Path("output/routes").mkdir(parents=True, exist_ok=True)

        map_width, map_height = self.map_image.size
        info_width = 100
        final_width = map_width + info_width
        final_height = max(map_height, 800)

        final_img = Image.new("RGB", (final_width, final_height), "white")

        # Создаем чистую карту для маршрута
        clean_map = self.map_processor.get_markup_image()
        draw_clean = ImageDraw.Draw(clean_map)
        
        # Рисуем товары на чистой карте
        for product_id, (x, y) in self.route_optimizer.placed_products.items():
            if product_id in self.route_optimizer.access_points:
                draw_clean.ellipse([x - 3, y - 3, x + 3, y + 3], fill="yellow", outline="orange")
                access_x, access_y = self.route_optimizer.access_points[product_id]
                draw_clean.ellipse([access_x - 2, access_y - 2, access_x + 2, access_y + 2], fill="lightgreen", outline="green")
                draw_clean.line([x, y, access_x, access_y], fill="lightblue", width=1)
            else:
                draw_clean.ellipse([x - 3, y - 3, x + 3, y + 3], fill="orange", outline="red")
            draw_clean.text((x + 5, y - 5), product_id, fill="blue")

        # Рисование маршрута
        draw_route = ImageDraw.Draw(clean_map)

        if len(path) > 1:
            for i in range(len(path) - 1):
                draw_route.line([path[i], path[i + 1]], fill="red", width=2)

        # Выделение товаров в маршруте
        for idx, product_id in enumerate(products, 1):
            if product_id in self.route_optimizer.access_points:
                ax, ay = self.route_optimizer.access_points[product_id]
                draw_route.ellipse(
                    [ax - 7, ay - 7, ax + 7, ay + 7],
                    fill="yellow",
                    outline="orange",
                    width=2,
                )
                draw_route.text((ax - 4, ay - 6), str(idx), fill="black")
                
                if product_id in self.route_optimizer.placed_products:
                    x, y = self.route_optimizer.placed_products[product_id]
                    draw_route.line([ax, ay, x, y], fill="orange", width=1)
                    draw_route.ellipse([x - 4, y - 4, x + 4, y + 4], fill="yellow", outline="red")

        # Отметка старта и финиша
        if self.start_point:
            x, y = self.start_point
            draw_route.ellipse([x - 6, y - 6, x + 6, y + 6], fill="green", outline="darkgreen", width=2)
            draw_route.text((x + 8, y - 8), "START", fill="green")

        if self.end_point:
            x, y = self.end_point
            draw_route.ellipse([x - 6, y - 6, x + 6, y + 6], fill="red", outline="darkred", width=2)
            draw_route.text((x + 8, y - 8), "FINISH", fill="red")

        # Уменьшаем и размещаем карту
        route_scale_factor = 0.8
        route_img_resized = clean_map.resize(
            (int(map_width * route_scale_factor), int(map_height * route_scale_factor)), 
            Image.Resampling.LANCZOS
        )
        
        bordered_map = Image.new("RGB", 
                                (route_img_resized.width + 4, route_img_resized.height + 4), 
                                "black")
        bordered_map.paste(route_img_resized, (2, 2))

        # Информационная панель
        draw = ImageDraw.Draw(final_img)

        try:
            font_title = ImageFont.truetype("arial.ttf", 20)
            font_normal = ImageFont.truetype("arial.ttf", 16)
            font_small = ImageFont.truetype("arial.ttf", 14)
        except:
            font_title = ImageFont.load_default()
            font_normal = ImageFont.load_default()
            font_small = ImageFont.load_default()

        from datetime import datetime
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Информация о выборке
        y_pos = 10
        # Вычисляем номер ночной сессии (1-5)
        night_session = ((route_id - 1) // 15) + 1
        draw.text((10, y_pos), f"Ночная сессия испытаний №{night_session}", fill="darkblue", font=font_normal)
        y_pos += 18
        draw.text((10, y_pos), f"Испытание #{route_id}", fill="black", font=font_title)
        y_pos += 25
        draw.text((10, y_pos), f"Расстояние: {distance:.2f} м", fill="black", font=font_normal)
        y_pos += 18
        draw.text((10, y_pos), f"Товаров: {len(products)}", fill="black", font=font_normal)
        y_pos += 18
        draw.text((10, y_pos), f"Создано: {timestamp}", fill="gray", font=font_small)

        # Размещение карты
        map_margin = 20
        route_y_pos = 120
        final_img.paste(bordered_map, (map_margin, route_y_pos))

        # Список товаров справа от карты
        map_right_edge = map_margin + bordered_map.width
        gap_between = 30
        info_x = map_right_edge + gap_between

        products_y_start = 10
        y_pos = products_y_start
        draw.text((info_x, y_pos), "ТОВАРЫ ДЛЯ СБОРА:", fill="black", font=font_title)
        y_pos += 30

        def wrap_text(text, max_length=30):
            if len(text) <= max_length:
                return [text]
            words = text.split()
            lines = []
            current_line = ""
            for word in words:
                if len(current_line + " " + word) <= max_length:
                    current_line += " " + word if current_line else word
                else:
                    if current_line:
                        lines.append(current_line)
                    current_line = word
            if current_line:
                lines.append(current_line)
            return lines

        for idx, product_id in enumerate(products, 1):
            if product_id in self.route_optimizer.products:
                product = self.route_optimizer.products[product_id]

                estimated_height_needed = y_pos + 150
                if estimated_height_needed > final_height:
                    new_height = estimated_height_needed + 100
                    new_img = Image.new("RGB", (final_width, new_height), "white")
                    
                    draw_area = final_img.crop((0, 0, final_width, final_height))
                    new_img.paste(draw_area, (0, 0))
                    
                    final_img = new_img
                    final_height = new_height
                    draw = ImageDraw.Draw(final_img)
                    
                    final_img.paste(bordered_map, (map_margin, route_y_pos))

                draw.text((info_x, y_pos), f"{idx}. ID {product.id}", fill="black", font=font_normal)
                y_pos += 20
                
                wrapped_name = wrap_text(product.name, 30)
                for line in wrapped_name:
                    draw.text((info_x + 20, y_pos), line, fill="gray", font=font_normal)
                    y_pos += 15
                
                y_pos += 5

                photo_path = f"data/photos/{product.id}.jpg"
                if not Path(photo_path).exists():
                    photo_path = f"data/photos/{product.id}.png"

                if Path(photo_path).exists():
                    try:
                        product_img = Image.open(photo_path)
                        product_img.thumbnail((70, 70), Image.Resampling.LANCZOS)
                        final_img.paste(product_img, (info_x + 20, y_pos))
                        y_pos += 75
                    except:
                        y_pos += 5
                else:
                    draw.rectangle(
                        [(info_x + 20, y_pos), (info_x + 90, y_pos + 70)],
                        outline="gray",
                        width=1,
                    )
                    draw.text((info_x + 40, y_pos + 30), "Нет\nфото", fill="gray")
                    y_pos += 75

                y_pos += 15

        filepath = f"output/routes/route_{route_id}.png"
        final_img.save(filepath)

    def view_routes(self):
        """Просмотр сохраненных маршрутов"""
        import glob

        route_files = glob.glob("output/routes/route_*_info.json")
        if not route_files:
            messagebox.showinfo("Информация", "Нет сохраненных маршрутов")
            return

        viewer = tk.Toplevel(self.root)
        viewer.title("Просмотр маршрутов")
        viewer.geometry("600x400")

        list_frame = tk.Frame(viewer)
        list_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)

        tk.Label(list_frame, text="Сохраненные маршруты:", font=("Arial", 12, "bold")).pack()

        listbox = tk.Listbox(list_frame, width=40, height=20)
        listbox.pack(fill=tk.BOTH, expand=True, pady=5)

        info_frame = tk.Frame(viewer)
        info_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)

        info_text = tk.Text(info_frame, width=40, height=20, wrap=tk.WORD)
        info_text.pack(fill=tk.BOTH, expand=True)

        routes_data = []

        for filepath in sorted(route_files):
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                routes_data.append(data)
                listbox.insert(
                    tk.END,
                    f"Маршрут {data['route_id']}: {data['distance_meters']:.1f} м, "
                    f"{len(data['products'])} товаров",
                )

        def on_select(event):
            selection = listbox.curselection()
            if selection:
                route = routes_data[selection[0]]
                info_text.delete(1.0, tk.END)
                info_text.insert(tk.END, f"МАРШРУТ №{route['route_id']}\n")
                info_text.insert(tk.END, "=" * 30 + "\n\n")
                info_text.insert(tk.END, f"Расстояние: {route['distance_meters']:.2f} м\n")
                info_text.insert(tk.END, f"Точек пути: {route['path_length']}\n\n")
                info_text.insert(tk.END, "Товары для сбора:\n")
                info_text.insert(tk.END, "-" * 20 + "\n")
                for i, product in enumerate(route["product_details"], 1):
                    info_text.insert(
                        tk.END,
                        f"{i}. {product['id']}: {product['name']}\n"
                        f"   Позиция: ({product['coordinates'][0]}, {product['coordinates'][1]})\n",
                    )
                    if "access_point" in product:
                        info_text.insert(
                            tk.END,
                            f"   Доступ: ({product['access_point'][0]}, {product['access_point'][1]})\n",
                        )
                    if "amount" in product:
                        info_text.insert(tk.END, f"   Количество: {product['amount']}\n")

        def open_image():
            selection = listbox.curselection()
            if selection:
                route_id = routes_data[selection[0]]["route_id"]
                image_path = Path(f"output/routes/route_{route_id}.png").absolute()
                if image_path.exists():
                    import os
                    if os.name == "nt":
                        os.startfile(str(image_path))
                    else:
                        os.system(f"open '{image_path}' 2>/dev/null || xdg-open '{image_path}'")
                else:
                    messagebox.showwarning("Внимание", "Изображение маршрута не найдено")

        listbox.bind("<<ListboxSelect>>", on_select)

        tk.Button(list_frame, text="Открыть изображение", command=open_image).pack(pady=5)
        tk.Button(viewer, text="Закрыть", command=viewer.destroy).pack(side=tk.BOTTOM, pady=10)

    def optimize_samples_order(self):
        """Оптимизация порядка выборок для минимизации перестановок товаров"""
        import glob
        import json
        
        # Загружаем существующие маршруты
        route_files = glob.glob("output/routes/route_*_info.json")
        if not route_files:
            messagebox.showwarning("Внимание", "Нет сгенерированных маршрутов для оптимизации")
            return
        
        # Извлекаем выборки из файлов
        routes_data = []
        for file in sorted(route_files, key=lambda x: int(x.split('_')[1])):
            with open(file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                routes_data.append(data['products'])
        
        # Оптимизируем порядок
        optimized_samples = self.route_optimizer.optimize_samples_order(routes_data)
        
        # Группируем по ночам
        night_groups = self.route_optimizer.group_samples_by_nights(optimized_samples)
        
        # Анализируем эффективность
        stats = self.route_optimizer.analyze_night_efficiency(night_groups)
        
        # Сохраняем оптимизированные выборки
        self.optimized_samples = optimized_samples  

        # Показываем результаты
        self.show_optimization_results(night_groups, stats)

    def show_optimization_results(self, night_groups, stats):
        """Показ результатов оптимизации"""
        result_window = tk.Toplevel(self.root)
        result_window.title("Результаты оптимизации порядка выборок")
        result_window.geometry("800x600")
        
        # Общая статистика
        stats_frame = tk.Frame(result_window)
        stats_frame.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Label(stats_frame, text="ОБЩАЯ СТАТИСТИКА", font=("Arial", 14, "bold")).pack()
        tk.Label(stats_frame, text=f"Всего уникальных товаров: {stats['total_unique_products']}").pack()
        tk.Label(stats_frame, text=f"Среднее количество товаров за ночь: {stats['avg_products_per_night']:.1f}").pack()
        tk.Label(stats_frame, text=f"Эффективность оптимизации: {stats['efficiency_score']:.1%}").pack()
        
        # Текстовое поле с результатами
        text_frame = tk.Frame(result_window)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        text_widget = tk.Text(text_frame, wrap=tk.WORD)
        scrollbar = tk.Scrollbar(text_frame, orient=tk.VERTICAL, command=text_widget.yview)
        text_widget.config(yscrollcommand=scrollbar.set)
        
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Заполняем результаты
        result_text = ""
        for night_info in stats['nights']:
            result_text += f"\n=== НОЧЬ {night_info['night']} ===\n"
            result_text += f"Экспериментов: {night_info['experiments']}\n"
            result_text += f"Уникальных товаров: {night_info['unique_products']}\n"
            result_text += f"Общее количество смен товаров: {night_info['total_changes']}\n"
            result_text += f"Среднее количество смен за эксперимент: {night_info['avg_changes_per_experiment']:.1f}\n"
            result_text += f"Товары: {', '.join(night_info['products'])}\n"
            result_text += "\n"
        
        text_widget.insert(tk.END, result_text)
        text_widget.config(state=tk.DISABLED)
        
        # Кнопки
        button_frame = tk.Frame(result_window)
        button_frame.pack(fill=tk.X, padx=10, pady=5)
        
        def save_optimized():
            # Сохраняем оптимизированный порядок
            filepath = filedialog.asksaveasfilename(
                title="Сохранить план экспериментов",
                defaultextension=".txt",
                filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
            )
            if filepath:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write("ПЛАН ПРОВЕДЕНИЯ ЭКСПЕРИМЕНТОВ\n")
                    f.write("=" * 50 + "\n\n")
                    
                    for night_idx, night_samples in enumerate(night_groups):
                        f.write(f"НОЧЬ {night_idx + 1} ({len(night_samples)} экспериментов)\n")
                        f.write("-" * 30 + "\n")
                        
                        for exp_idx, sample in enumerate(night_samples):
                            f.write(f"Эксперимент {exp_idx + 1}: {', '.join(sample)}\n")
                        
                        # Список уникальных товаров для ночи
                        night_products = set()
                        for sample in night_samples:
                            night_products.update(sample)
                        f.write(f"\nТовары для подготовки ({len(night_products)} шт.): {', '.join(sorted(night_products))}\n\n")
                    
                    f.write(f"\nОБЩАЯ СТАТИСТИКА:\n")
                    f.write(f"Всего уникальных товаров: {stats['total_unique_products']}\n")
                    f.write(f"Эффективность: {stats['efficiency_score']:.1%}\n")
                
                messagebox.showinfo("Успех", f"План сохранен в {filepath}")

        def save_report():
            filepath = filedialog.asksaveasfilename(
                title="Сохранить отчет оптимизации",
                defaultextension=".txt",
                filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
            )
            if filepath:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write("ОТЧЕТ ПО ОПТИМИЗАЦИИ ВЫБОРОК\n")
                    f.write("=" * 50 + "\n\n")
                    
                    f.write("ОБЩАЯ СТАТИСТИКА:\n")
                    f.write(f"Всего уникальных товаров: {stats['total_unique_products']}\n")
                    f.write(f"Среднее количество товаров за ночь: {stats['avg_products_per_night']:.1f}\n")
                    f.write(f"Эффективность оптимизации: {stats['efficiency_score']:.1%}\n\n")
                    
                    for night_info in stats['nights']:
                        f.write(f"=== НОЧЬ {night_info['night']} ===\n")
                        f.write(f"Экспериментов: {night_info['experiments']}\n")
                        f.write(f"Уникальных товаров: {night_info['unique_products']}\n")
                        f.write(f"Общее количество смен товаров: {night_info['total_changes']}\n")
                        f.write(f"Среднее количество смен за эксперимент: {night_info['avg_changes_per_experiment']:.1f}\n")
                        f.write(f"Эффективность ночи: {night_info['efficiency']:.1%}\n")
                        f.write(f"Товары: {', '.join(night_info['products'])}\n\n")
                
                messagebox.showinfo("Успех", f"Отчет сохранен в {filepath}")

        tk.Button(button_frame, text="Сохранить план", command=save_optimized).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Сохранить отчет", command=save_report).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Экспорт CSV", command=self.export_csv).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Дистанции CSV", command=self.export_distances_csv).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Закрыть", command=result_window.destroy).pack(side=tk.RIGHT, padx=5)
    
    def auto_load_last_config(self):
        """Автоматическая загрузка последней конфигурации"""
        config = self.route_optimizer.load_config()
        if not config:
            return
        
        try:
            # Загружаем карту
            if config.get('map_path') and Path(config['map_path']).exists():
                self.current_map_path = config['map_path']
                self.map_processor.load_map(config['map_path'])
                
            # Загружаем товары
            if config.get('products_path') and Path(config['products_path']).exists():
                self.route_optimizer.load_products(config['products_path'])
                self.current_products_path = config['products_path']
                
            # Загружаем разметку
            if config.get('markup_path') and Path(config['markup_path']).exists():
                self.map_processor.load_markup(config['markup_path'])
                self.current_markup_path = config['markup_path']
                
            # Восстанавливаем точки старт/финиш
            start_point = config.get('start_point')
            end_point = config.get('end_point')
            self.start_point = tuple(start_point) if start_point and len(start_point) == 2 else None
            self.end_point = tuple(end_point) if end_point and len(end_point) == 2 else None
            self.scale_set = config.get('scale_set', False)
            self.robot_radius_set = config.get('robot_radius_set', False)
            
            self.update_status()
            self.display_map()
            
            # Обновляем информацию
            count = len(self.route_optimizer.products)
            placed = len(self.route_optimizer.placed_products)
            access_count = len(self.route_optimizer.access_points)
            
            info_text = f"Конфигурация загружена: {count} товаров, {placed} размещено, {access_count} с доступом"
            if self.route_optimizer.has_amount_data():
                with_amount = sum(1 for p in self.route_optimizer.products.values() if p.amount > 0)
                info_text += f", {with_amount} с количеством"
                
            self.info_label.config(text=info_text)
            
        except Exception as e:
            print(f"Ошибка загрузки конфигурации: {e}")

    def save_current_config(self):
        """Сохранение текущей конфигурации"""
        config = {
            "map_path": getattr(self, 'current_map_path', ''),
            "products_path": getattr(self, 'current_products_path', ''),
            "markup_path": getattr(self, 'current_markup_path', ''),
            "start_point": self.start_point,
            "end_point": self.end_point,
            "scale_set": self.scale_set,
            "robot_radius_set": self.robot_radius_set
        }
        
        Path("data").mkdir(exist_ok=True)
        with open("data/last_config.json", 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)

    def export_distances_csv(self):
        """Экспорт дистанций между точками маршрутов в CSV"""
        try:
            count = self.route_optimizer.export_distances_to_csv()
            messagebox.showinfo("Успех", f"Экспортировано {count} маршрутов с дистанциями в output/routes/distances_summary.csv")
        except ValueError as e:
            messagebox.showwarning("Внимание", str(e))
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка экспорта дистанций: {e}")

if __name__ == "__main__":
    root = tk.Tk()
    root.title("Оптимизатор маршрутов склада")
    app = WarehouseGUI(root)
    root.mainloop()