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
        tk.Button(control_frame2, text="Очистить разметку", command=self.clear_markup).pack(side=tk.LEFT, padx=2)
        tk.Button(control_frame2, text="Сохранить разметку", command=self.save_markup).pack(side=tk.LEFT, padx=2)
        tk.Button(control_frame2, text="Загрузить разметку", command=self.load_markup).pack(side=tk.LEFT, padx=2)

        # Панель управления - третья строка
        control_frame3 = tk.Frame(self.root)
        control_frame3.pack(side=tk.TOP, fill=tk.X, padx=5, pady=2)

        tk.Button(control_frame3, text="Установить старт/финиш", command=self.set_route_points_mode).pack(side=tk.LEFT, padx=2)
        tk.Button(control_frame3, text="Генерировать маршруты", command=self.generate_routes).pack(side=tk.LEFT, padx=2)
        tk.Button(control_frame3, text="Сохранить товары", command=self.save_products).pack(side=tk.LEFT, padx=2)
        tk.Button(control_frame3, text="Просмотр маршрутов", command=self.view_routes).pack(side=tk.LEFT, padx=2)
        tk.Button(control_frame3, text="Экспорт в CSV", command=self.export_csv).pack(side=tk.LEFT, padx=2)

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
                self.scale_set = True
                self.robot_radius_set = True
                self.update_status()
                self.display_map()
                messagebox.showinfo("Успех", "Разметка загружена")
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

        info_frame = tk.Frame(selector)
        info_frame.pack(padx=10, pady=5)
        tk.Label(
            info_frame,
            text=f"Размещено: {placed_count}/{total_count} товаров, доступно: {access_count}",
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

        listbox = tk.Listbox(selector, width=50, height=20)
        listbox.pack(padx=10, pady=10)

        for product in self.route_optimizer.products.values():
            status = "✓" if product.id in self.route_optimizer.access_points else ("◐" if product.x >= 0 else "✗")
            listbox.insert(tk.END, f"{status} {product.id}: {product.name}")

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
            self.info_label.config(
                text=f"Размещено товаров: {placed_count}/{total_count}, доступно: {access_count}"
            )
            selector.destroy()

        button_frame = tk.Frame(selector)
        button_frame.pack(pady=5)
        tk.Button(button_frame, text="Выбрать", command=on_select).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Завершить", command=on_cancel).pack(side=tk.LEFT, padx=5)

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
                self.route_optimizer.load_products(filepath)
                self.display_map()
                count = len(self.route_optimizer.products)
                placed = len(self.route_optimizer.placed_products)
                access_count = len(self.route_optimizer.access_points)
                self.info_label.config(
                    text=f"Загружено товаров: {count}, размещено: {placed}, с доступом: {access_count}"
                )
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

        elif self.mode == "place" and hasattr(self, "selected_product_id"):
            ix, iy = int(x), int(y)

            if self.map_processor.is_shelf(ix, iy):
                access = self.map_processor.find_nearest_walkable(ix, iy, max_radius=50)
                if access:
                    self.route_optimizer.place_product(self.selected_product_id, ix, iy, access)
                    self.display_map()
                    self.info_label.config(text=f"Товар размещен на стеллаже с точкой доступа")
                    self.show_product_selector()
                else:
                    messagebox.showwarning("Внимание", "К этому месту нет доступа!")
            else:
                found = False
                for r in range(1, 50):
                    for dx in range(-r, r + 1):
                        for dy in range(-r, r + 1):
                            sx, sy = ix + dx, iy + dy
                            if self.map_processor.is_shelf(sx, sy):
                                access = self.map_processor.find_nearest_walkable(sx, sy, max_radius=50)
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
                else:
                    nearest = self.map_processor.find_nearest_walkable(ix, iy, max_radius=10)
                    if nearest:
                        self.end_point = nearest
                        self.display_map()
                        self.info_label.config(
                            text=f"Старт: {self.start_point}, Финиш: {self.end_point}"
                        )
                        self.mode = "view"
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
                    self.info_label.config(text=f"Товар: {product.id} - {product.name} ({access_status})")
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
        self.photo_image = ImageTk.PhotoImage(img)

        self.canvas.delete("all")
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.photo_image)
        self.canvas.config(scrollregion=self.canvas.bbox("all"))

    # Остальные методы остаются без изменений
    def generate_routes(self):
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

            progress = tk.Toplevel(self.root)
            progress.title("Генерация маршрутов")
            progress_label = tk.Label(progress, text="Инициализация...")
            progress_label.pack(padx=20, pady=10)
            progress_bar = ttk.Progressbar(progress, length=300, mode="determinate", maximum=num_samples)
            progress_bar.pack(padx=20, pady=10)

            successful_routes = 0
            failed_routes = 0

            for i, sample in enumerate(samples):
                progress_label.config(text=f"Обработка маршрута {i+1}/{num_samples}")
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
                    successful_routes += 1
                else:
                    failed_routes += 1

                progress_bar["value"] = i + 1
                progress.update()

            progress.destroy()

            if successful_routes > 0:
                messagebox.showinfo(
                    "Успех",
                    f"Сгенерировано маршрутов: {successful_routes}\n"
                    f"Не удалось построить: {failed_routes}\n"
                    f"Сохранено в: output/routes/",
                )
            else:
                messagebox.showwarning(
                    "Внимание",
                    f"Не удалось построить ни одного маршрута.\n"
                    f"Проверьте:\n"
                    f"- Точки доступа к товарам (зеленые точки на карте)\n"
                    f"- Проходимость между стартом, товарами и финишем\n"
                    f"- Размер радиуса робота\n"
                    f"Товаров с доступом: {access_count}",
                )

        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка генерации: {e}")

    def save_route_image(self, route_id: int, path: List[tuple], products: List[str], distance: float):
        if not self.map_image:
            return

        Path("output/routes").mkdir(parents=True, exist_ok=True)

        map_width, map_height = self.map_image.size
        info_width = 150
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
            font_title = ImageFont.truetype("arial.ttf", 16)
            font_normal = ImageFont.truetype("arial.ttf", 12)
            font_small = ImageFont.truetype("arial.ttf", 10)
        except:
            font_title = ImageFont.load_default()
            font_normal = ImageFont.load_default()
            font_small = ImageFont.load_default()

        from datetime import datetime
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Информация о выборке
        y_pos = 10
        draw.text((10, y_pos), f"ВЫБОРКА #{route_id}", fill="black", font=font_title)
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


if __name__ == "__main__":
    root = tk.Tk()
    root.title("Оптимизатор маршрутов склада")
    app = WarehouseGUI(root)
    root.mainloop()