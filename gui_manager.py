import json
import math
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk
from typing import List
from datetime import datetime

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
        
        # Для зума карты
        self.zoom_level = 1.0
        self.min_zoom = 0.1
        self.max_zoom = 5.0
        
        # Для рисования стен
        self.current_wall_chain = []
        self.temp_line_start = None
        
        # Для рисования стеллажей
        self.temp_rect_start = None

        self.setup_ui()
        self.optimized_samples = None
        self.current_config_name = None

    def setup_ui(self):
        # Создаем главное меню
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # Меню "Файл"
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Файл", menu=file_menu)
        file_menu.add_command(label="Новая конфигурация", command=self.new_config)
        file_menu.add_command(label="Открыть конфигурацию", command=self.open_config)
        file_menu.add_command(label="Сохранить конфигурацию", command=self.save_config)
        file_menu.add_command(label="Сохранить как...", command=self.save_config_as)
        file_menu.add_separator()
        file_menu.add_command(label="Экспорт результатов в CSV", command=self.export_csv)
        file_menu.add_command(label="Экспорт дистанций в CSV", command=self.export_distances_csv)
        
        # Меню "Конфигурация"
        config_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Конфигурация", menu=config_menu)
        config_menu.add_command(label="Загрузить карту", command=self.load_map)
        config_menu.add_command(label="Установить масштаб", command=self.set_scale_mode)
        config_menu.add_command(label="Установить радиус робота", command=self.set_robot_radius)
        config_menu.add_command(label="Установить старт/финиш", command=self.set_route_points_mode)
        
        # Меню "Разметка"
        markup_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Разметка", menu=markup_menu)
        markup_menu.add_command(label="Рисовать стены", command=self.draw_walls_mode)
        markup_menu.add_command(label="Рисовать стеллажи", command=self.draw_shelves_mode)
        markup_menu.add_command(label="Удалить стеллаж", command=self.remove_shelf_mode)
        markup_menu.add_command(label="Очистить разметку", command=self.clear_markup)
        markup_menu.add_separator()
        markup_menu.add_command(label="Сохранить разметку", command=self.save_markup)
        markup_menu.add_command(label="Загрузить разметку", command=self.load_markup)
        
        # Меню "Продукты"
        products_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Продукты", menu=products_menu)
        products_menu.add_command(label="Загрузить список товаров", command=self.load_products)
        products_menu.add_command(label="Разместить товары", command=self.place_products_mode)
        products_menu.add_command(label="Сохранить товары", command=self.save_products)
        
        # Меню "Маршруты"
        routes_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Маршруты", menu=routes_menu)
        routes_menu.add_command(label="Генерировать маршруты", command=self.generate_routes)
        routes_menu.add_command(label="Генерировать с ограничениями", command=self.generate_routes_with_limits)
        routes_menu.add_separator()
        routes_menu.add_command(label="Просмотр маршрутов", command=self.view_routes)

        # Информационная панель
        info_frame = tk.Frame(self.root)
        info_frame.pack(side=tk.TOP, fill=tk.X, padx=5)

        self.info_label = tk.Label(info_frame, text="Создайте новую конфигурацию или откройте существующую", anchor=tk.W)
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

        # Обработка колеса мыши
        self.canvas.bind("<MouseWheel>", self.on_mousewheel)
        self.canvas.bind("<Button-4>", self.on_mousewheel)  # Linux
        self.canvas.bind("<Button-5>", self.on_mousewheel)  # Linux
                
        # Привязка клавиш
        self.root.bind("<KeyPress>", self.on_key_press)
        self.root.focus_set()

        # Инициализация
        self.current_config_name = None
        self.update_status()
    
    def on_key_press(self, event):
        """Обработка нажатий клавиш"""
        if event.keysym == "Escape":
            if self.mode == "draw_walls" and self.current_wall_chain:
                # Сохраняем текущую цепочку стен
                self.save_wall_chain()
                self.info_label.config(text="Цепочка стен сохранена. Нажмите для начала новой цепочки")
    
    def on_mousewheel(self, event):
        """Обработка событий колеса мыши"""
        # Определяем направление прокрутки
        if event.num == 4 or event.delta > 0:
            delta = 1
        elif event.num == 5 or event.delta < 0:
            delta = -1
        else:
            return

        # Проверяем модификаторы
        ctrl_pressed = (event.state & 0x4) != 0  # Control
        shift_pressed = (event.state & 0x1) != 0  # Shift

        if ctrl_pressed:
            # Зум
            if delta > 0:
                self.zoom_in(event.x, event.y)
            else:
                self.zoom_out(event.x, event.y)
        elif shift_pressed:
            # Горизонтальная прокрутка
            if delta > 0:
                self.canvas.xview_scroll(-1, "units")
            else:
                self.canvas.xview_scroll(1, "units")
        else:
            # Вертикальная прокрутка
            if delta > 0:
                self.canvas.yview_scroll(-1, "units")
            else:
                self.canvas.yview_scroll(1, "units")

    def zoom_in(self, mouse_x, mouse_y):
        """Увеличение масштаба"""
        if self.zoom_level >= self.max_zoom:
            return
        
        # Сохраняем текущую позицию мыши относительно canvas
        old_canvasx = self.canvas.canvasx(mouse_x)
        old_canvasy = self.canvas.canvasy(mouse_y)
        
        # Увеличиваем масштаб
        self.zoom_level *= 1.2
        if self.zoom_level > self.max_zoom:
            self.zoom_level = self.max_zoom
        
        self.apply_zoom()
        
        # Корректируем позицию скролла чтобы мышь осталась на том же месте
        new_canvasx = old_canvasx * 1.2
        new_canvasy = old_canvasy * 1.2
        
        self.canvas.scan_mark(int(mouse_x), int(mouse_y))
        self.canvas.scan_dragto(int(mouse_x - (new_canvasx - old_canvasx)), 
                            int(mouse_y - (new_canvasy - old_canvasy)), gain=1)

    def zoom_out(self, mouse_x, mouse_y):
        """Уменьшение масштаба"""
        if self.zoom_level <= self.min_zoom:
            return
        
        # Сохраняем текущую позицию мыши относительно canvas
        old_canvasx = self.canvas.canvasx(mouse_x)
        old_canvasy = self.canvas.canvasy(mouse_y)
        
        # Уменьшаем масштаб
        self.zoom_level /= 1.2
        if self.zoom_level < self.min_zoom:
            self.zoom_level = self.min_zoom
        
        self.apply_zoom()
        
        # Корректируем позицию скролла
        new_canvasx = old_canvasx / 1.2
        new_canvasy = old_canvasy / 1.2
        
        self.canvas.scan_mark(int(mouse_x), int(mouse_y))
        self.canvas.scan_dragto(int(mouse_x - (new_canvasx - old_canvasx)), 
                            int(mouse_y - (new_canvasy - old_canvasy)), gain=1)

    def apply_zoom(self):
        """Применение масштаба к изображению"""
        if not self.map_image:
            return
        
        # Создаем изображение нужного размера
        original_width, original_height = self.map_image.size
        new_width = int(original_width * self.zoom_level)
        new_height = int(original_height * self.zoom_level)
        
        # Применяем масштаб
        if self.zoom_level == 1.0:
            scaled_image = self.map_image
        else:
            scaled_image = self.map_image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # Обновляем PhotoImage
        self.photo_image = ImageTk.PhotoImage(scaled_image)
        
        # Очищаем canvas и добавляем новое изображение
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.photo_image, tags="map_image")
        self.canvas.tag_lower("map_image")
        
        # Обновляем область прокрутки
        self.canvas.config(scrollregion=(0, 0, new_width, new_height))
        
        # Перерисовываем элементы интерфейса с учетом масштаба
        self.draw_scaled_elements()

    def restore_scroll_position(self, scroll_x, scroll_y):
        """Восстановление позиции скролла"""
        try:
            if scroll_x != 0:
                self.canvas.xview_moveto(scroll_x)
            if scroll_y != 0:
                self.canvas.yview_moveto(scroll_y)
        except:
            pass

    def draw_scaled_elements(self):
        """Перерисовка элементов интерфейса с учетом масштаба"""
        zoom = self.zoom_level
        
        # Удаляем все интерфейсные элементы
        self.canvas.delete("interface_elements")

        # Отрисовка точек масштаба (если режим установки масштаба активен)
        if self.mode == "scale":
            for point in self.scale_points:
                scaled_x, scaled_y = point[0] * zoom, point[1] * zoom
                self.canvas.create_oval(
                    scaled_x - 3, scaled_y - 3, scaled_x + 3, scaled_y + 3, 
                    fill="red", tags="scale"
                )
        
        # Отрисовка размещенных товаров
        for product_id, (x, y) in self.route_optimizer.placed_products.items():
            scaled_x, scaled_y = x * zoom, y * zoom
            
            if product_id in self.route_optimizer.access_points:
                # Товар с доступом
                self.canvas.create_oval(
                    scaled_x - 3*zoom, scaled_y - 3*zoom, 
                    scaled_x + 3*zoom, scaled_y + 3*zoom, 
                    fill="yellow", outline="orange", width=max(1, int(zoom))
                )
                
                access_x, access_y = self.route_optimizer.access_points[product_id]
                scaled_ax, scaled_ay = access_x * zoom, access_y * zoom
                
                self.canvas.create_oval(
                    scaled_ax - 2*zoom, scaled_ay - 2*zoom, 
                    scaled_ax + 2*zoom, scaled_ay + 2*zoom, 
                    fill="lightgreen", outline="green", width=max(1, int(zoom))
                )
                
                self.canvas.create_line(
                    scaled_x, scaled_y, scaled_ax, scaled_ay, 
                    fill="lightblue", width=max(1, int(zoom))
                )
            else:
                # Товар без доступа
                self.canvas.create_oval(
                    scaled_x - 3*zoom, scaled_y - 3*zoom, 
                    scaled_x + 3*zoom, scaled_y + 3*zoom, 
                    fill="orange", outline="red", width=max(1, int(zoom))
                )
            
            # Подпись товара
            if zoom >= 0.5:  # Показываем текст только при достаточном масштабе
                self.canvas.create_text(
                    scaled_x + 5*zoom, scaled_y - 5*zoom, 
                    text=product_id, fill="blue", 
                    font=("Arial", max(8, int(8*zoom)))
                )

        # Отрисовка точек старта и финиша
        if self.start_point:
            x, y = self.start_point
            scaled_x, scaled_y = x * zoom, y * zoom
            self.canvas.create_oval(
                scaled_x - 5*zoom, scaled_y - 5*zoom,
                scaled_x + 5*zoom, scaled_y + 5*zoom,
                fill="green", outline="darkgreen", width=max(1, int(2*zoom)),
                tags="interface_elements"
            )
            if zoom >= 0.5:
                self.canvas.create_text(
                    scaled_x + 7*zoom, scaled_y - 5*zoom, 
                    text="START", fill="green", 
                    font=("Arial", max(8, int(8*zoom))),
                    tags="interface_elements"
                )

        if self.end_point:
            x, y = self.end_point
            scaled_x, scaled_y = x * zoom, y * zoom
            self.canvas.create_oval(
                scaled_x - 5*zoom, scaled_y - 5*zoom,
                scaled_x + 5*zoom, scaled_y + 5*zoom,
                fill="red", outline="darkred", width=max(1, int(2*zoom)),
                tags="interface_elements"
            )
            if zoom >= 0.5:
                self.canvas.create_text(
                    scaled_x + 7*zoom, scaled_y - 5*zoom, 
                    text="FINISH", fill="red", 
                    font=("Arial", max(8, int(8*zoom))),
                    tags="interface_elements"
                )
                
        # Отрисовка временных элементов для рисования стен
        if self.mode == "draw_walls" and self.current_wall_chain:
            for point in self.current_wall_chain:
                scaled_x, scaled_y = point[0] * zoom, point[1] * zoom
                self.canvas.create_oval(
                    scaled_x - 2, scaled_y - 2, scaled_x + 2, scaled_y + 2, 
                    fill="red", tags="interface_elements"
                )
            
            # Линии между точками
            for i in range(len(self.current_wall_chain) - 1):
                x1, y1 = self.current_wall_chain[i]
                x2, y2 = self.current_wall_chain[i + 1]
                self.canvas.create_line(
                    x1 * zoom, y1 * zoom, x2 * zoom, y2 * zoom,
                    fill="red", width=2, tags="interface_elements"
                )
        
        # Временная точка для стеллажей
        if self.mode == "draw_shelves" and self.temp_rect_start:
            x, y = self.temp_rect_start
            scaled_x, scaled_y = x * zoom, y * zoom
            self.canvas.create_oval(
                scaled_x - 2, scaled_y - 2, scaled_x + 2, scaled_y + 2, 
                fill="blue", tags="interface_elements"
            )
    
    def refresh_temp_elements(self):
        """Обновление только временных элементов рисования"""
        zoom = self.zoom_level
        
        # Удаляем только временные элементы
        self.canvas.delete("temp_elements")
        
        # Отрисовка временных элементов для рисования стен
        if self.mode == "draw_walls" and self.current_wall_chain:
            for point in self.current_wall_chain:
                scaled_x, scaled_y = point[0] * zoom, point[1] * zoom
                self.canvas.create_oval(
                    scaled_x - 2, scaled_y - 2, scaled_x + 2, scaled_y + 2, 
                    fill="red", tags="temp_elements"
                )
            
            # Линии между точками
            for i in range(len(self.current_wall_chain) - 1):
                x1, y1 = self.current_wall_chain[i]
                x2, y2 = self.current_wall_chain[i + 1]
                self.canvas.create_line(
                    x1 * zoom, y1 * zoom, x2 * zoom, y2 * zoom,
                    fill="red", width=2, tags="temp_elements"
                )
        
        # Временная точка для стеллажей
        if self.mode == "draw_shelves" and self.temp_rect_start:
            x, y = self.temp_rect_start
            scaled_x, scaled_y = x * zoom, y * zoom
            self.canvas.create_oval(
                scaled_x - 2, scaled_y - 2, scaled_x + 2, scaled_y + 2, 
                fill="blue", tags="temp_elements"
            )

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
        self.full_display_refresh()
    
    def clear_markup(self):
        """Очистка разметки"""
        if messagebox.askyesno("Подтверждение", "Очистить всю разметку (стены и стеллажи)?"):
            self.map_processor.clear_markup()
            self.full_display_refresh()
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
                self.full_display_refresh()
                messagebox.showinfo("Успех", "Разметка загружена")
                self.auto_save()
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
                self.auto_save()
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось загрузить карту: {e}")
        

    def export_csv(self):
        """Экспорт всех маршрутов в CSV"""
        if not self.current_config_name:
            messagebox.showwarning("Предупреждение", "Нет активной конфигурации")
            return
            
        try:
            routes_dir = Path("output") / self.current_config_name / "routes"
            count = self.route_optimizer.export_routes_to_csv(str(routes_dir / "routes_summary.csv"), str(routes_dir))
            messagebox.showinfo("Успех", f"Экспортировано {count} маршрутов в {routes_dir}/routes_summary.csv")
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
        else:
            status_parts.append("Количества: нет")
        
        # Добавляем информацию о текущей конфигурации
        if hasattr(self, 'current_config_name') and self.current_config_name:
            status_parts.append(f"Конфигурация: {self.current_config_name}")

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
            self.refresh_elements_only()

    def set_scale_mode(self):
        self.mode = "scale"
        self.scale_points = []
        self.draw_scaled_elements()
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
    
    def refresh_elements_only(self):
        """Обновление только элементов интерфейса без сброса зума и позиции"""
        self.draw_scaled_elements()

    def full_display_refresh(self):
        """Полное обновление с сохранением зума и позиции"""
        if self.map_processor.original_image is None:
            return

        # Получаем изображение с разметкой
        img = self.map_processor.get_markup_image()
        if img is None:
            return

        self.map_image = img
        self.apply_zoom()  # Сохраняет позицию благодаря обновленному методу

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
        self.draw_scaled_elements()
        
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
                self.refresh_elements_only()
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
                self.auto_save() 
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
        # Пересчитываем координаты с учетом масштаба
        canvas_x = self.canvas.canvasx(event.x)
        canvas_y = self.canvas.canvasy(event.y)
        x = canvas_x / self.zoom_level
        y = canvas_y / self.zoom_level

        if self.mode == "scale":
            self.scale_points.append((x, y))
            # Отображаем точку с учетом зума
            scaled_x, scaled_y = x * self.zoom_level, y * self.zoom_level
            self.canvas.create_oval(
                scaled_x - 3, scaled_y - 3, scaled_x + 3, scaled_y + 3, 
                fill="red", tags="scale"
            )

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
                self.refresh_temp_elements()  # Вместо refresh_elements_only()
            else:
                # Заканчиваем линию
                self.current_wall_chain.append((ix, iy))
                
                # Проверяем замыкание (клик рядом с первой точкой)
                if len(self.current_wall_chain) > 2:
                    first_point = self.current_wall_chain[0]
                    dist = math.sqrt((ix - first_point[0])**2 + (iy - first_point[1])**2)
                    if dist < 10:  # Замыкаем если близко к первой точке
                        self.current_wall_chain.append(first_point)
                        self.save_wall_chain()
                        self.canvas.delete("temp_elements")  # Очищаем временные элементы
                        self.info_label.config(text="Многоугольник замкнут и сохранен")
                        return
                
                self.temp_line_start = (ix, iy)
                self.refresh_temp_elements()  # Обновляем только временные элементы

        elif self.mode == "draw_shelves":
            ix, iy = int(x), int(y)
            
            if not self.temp_rect_start:
                # Начинаем прямоугольник
                self.temp_rect_start = (ix, iy)
                self.refresh_temp_elements()  # Вместо refresh_elements_only()
                self.info_label.config(text="Кликните вторую точку для завершения прямоугольника")
            else:
                # Заканчиваем прямоугольник
                x1, y1 = self.temp_rect_start
                x2, y2 = ix, iy
                
                self.map_processor.add_shelf_rect(x1, y1, x2, y2)
                
                # Вместо full_display_refresh() используем более осторожный подход
                if self.map_processor.original_image is None:
                    return
                img = self.map_processor.get_markup_image()
                if img is None:
                    return
                self.map_image = img
                
                # Создаем масштабированное изображение без смещения карты
                original_width, original_height = self.map_image.size
                new_width = int(original_width * self.zoom_level)
                new_height = int(original_height * self.zoom_level)
                
                if self.zoom_level == 1.0:
                    scaled_image = self.map_image
                else:
                    scaled_image = self.map_image.resize((new_width, new_height), Image.Resampling.LANCZOS)
                
                self.photo_image = ImageTk.PhotoImage(scaled_image)
                
                # Обновляем только изображение карты, не трогая скролл
                self.canvas.delete("map_image")
                self.canvas.create_image(0, 0, anchor=tk.NW, image=self.photo_image, tags="map_image")
                self.canvas.tag_lower("map_image")  # Перемещаем карту на задний план
                
                self.temp_rect_start = None
                self.canvas.delete("temp_elements")  # Очищаем временные элементы
                self.draw_scaled_elements()  # Перерисовываем интерфейсные элементы
                self.info_label.config(text="Стеллаж добавлен. Кликните для следующего")

        elif self.mode == "remove_shelf":
            ix, iy = int(x), int(y)
            
            if self.map_processor.remove_shelf_at(ix, iy):
                # Тот же осторожный подход без смещения карты
                if self.map_processor.original_image is None:
                    return
                img = self.map_processor.get_markup_image()
                if img is None:
                    return
                self.map_image = img
                
                # Создаем масштабированное изображение без смещения карты
                original_width, original_height = self.map_image.size
                new_width = int(original_width * self.zoom_level)
                new_height = int(original_height * self.zoom_level)
                
                if self.zoom_level == 1.0:
                    scaled_image = self.map_image
                else:
                    scaled_image = self.map_image.resize((new_width, new_height), Image.Resampling.LANCZOS)
                
                self.photo_image = ImageTk.PhotoImage(scaled_image)
                
                # Обновляем только изображение карты, не трогая скролл
                self.canvas.delete("map_image")
                self.canvas.create_image(0, 0, anchor=tk.NW, image=self.photo_image, tags="map_image")
                self.canvas.tag_lower("map_image")  # Перемещаем карту на задний план
                
                self.draw_scaled_elements()  # Перерисовываем интерфейсные элементы
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
                    self.full_display_refresh()
                    self.info_label.config(text=f"Товар размещен на стеллаже с точкой доступа")
                    self.auto_save()
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
                                    self.full_display_refresh()
                                    self.info_label.config(text=f"Товар размещен на ближайшем стеллаже с точкой доступа")
                                    self.auto_save()
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
                    self.draw_scaled_elements()  # Вместо refresh_elements_only()
                    self.info_label.config(
                        text="Кликните в ПРОХОДЕ для установки точки ФИНИША"
                    )
                else:
                    nearest = self.map_processor.find_nearest_walkable(ix, iy, max_radius=10)
                    if nearest:
                        self.start_point = nearest
                        self.full_display_refresh()
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
                    self.draw_scaled_elements() 
                    self.info_label.config(
                        text=f"Старт: {self.start_point}, Финиш: {self.end_point}"
                    )
                    self.mode = "view"
                    self.auto_save()
                else:
                    nearest = self.map_processor.find_nearest_walkable(ix, iy, max_radius=10)
                    if nearest:
                        self.end_point = nearest
                        self.full_display_refresh()
                        self.info_label.config(
                            text=f"Старт: {self.start_point}, Финиш: {self.end_point}"
                        )
                        self.mode = "view"
                        self.auto_save() 
                    else:
                        messagebox.showwarning(
                            "Внимание",
                            "Точка финиша должна быть в проходе (белая область)!",
                        )

    def on_mouse_move(self, event):
        canvas_x = self.canvas.canvasx(event.x)
        canvas_y = self.canvas.canvasy(event.y)
        x = canvas_x / self.zoom_level
        y = canvas_y / self.zoom_level
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

        # Получаем изображение с разметкой (только стены и стеллажи)
        img = self.map_processor.get_markup_image()
        if img is None:
            return

        self.map_image = img
        self.photo_image = ImageTk.PhotoImage(img)

        self.canvas.delete("all")
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.photo_image, tags="map_image")
        self.canvas.tag_lower("map_image")
        self.canvas.config(scrollregion=self.canvas.bbox("all"))
        
        # Отрисовываем все интерактивные элементы
        self.draw_scaled_elements()

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
        if not self.current_config_name:
            messagebox.showwarning("Предупреждение", "Сначала сохраните конфигурацию")
            return
            
        # Создаем папку для маршрутов этой конфигурации
        routes_dir = Path("output") / self.current_config_name / "routes"
        routes_dir.mkdir(parents=True, exist_ok=True)
        
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
                self.route_optimizer.save_route_info(i + 1, ordered_sample, distance, path, str(routes_dir))
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
                f"Сохранено в: output/{self.current_config_name}/routes/",
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
        if not products or not path or not self.current_config_name:
            return
        
        routes_dir = Path("output") / self.current_config_name / "routes"
        routes_dir.mkdir(parents=True, exist_ok=True)
        
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
        
        filepath = routes_dir / f"route_{route_id}_path.json"
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(path_data, f, ensure_ascii=False, indent=2)

    def save_route_image(self, route_id: int, path: List[tuple], products: List[str], distance: float):
        if not self.map_image or not self.current_config_name:
            return

        routes_dir = Path("output") / self.current_config_name / "routes"
        routes_dir.mkdir(parents=True, exist_ok=True)

        map_width, map_height = self.map_image.size
        info_width = 200
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

        filepath = routes_dir / f"route_{route_id}.png"
        final_img.save(filepath)

    def view_routes(self):
        """Просмотр сохраненных маршрутов"""
        if not self.current_config_name:
            messagebox.showwarning("Предупреждение", "Нет активной конфигурации")
            return
            
        import glob

        routes_dir = Path("output") / self.current_config_name / "routes"
        route_files = glob.glob(str(routes_dir / "route_*_info.json"))
        
        if not route_files:
            messagebox.showinfo("Информация", f"Нет сохраненных маршрутов для конфигурации '{self.current_config_name}'")
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
                image_path = routes_dir / f"route_{route_id}.png"
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

    def export_distances_csv(self):
        """Экспорт дистанций между точками маршрутов в CSV"""
        if not self.current_config_name:
            messagebox.showwarning("Предупреждение", "Нет активной конфигурации")
            return
            
        try:
            routes_dir = Path("output") / self.current_config_name / "routes"
            count = self.route_optimizer.export_distances_to_csv(str(routes_dir / "distances_summary.csv"), str(routes_dir))
            messagebox.showinfo("Успех", f"Экспортировано {count} маршрутов с дистанциями в {routes_dir}/distances_summary.csv")
        except ValueError as e:
            messagebox.showwarning("Внимание", str(e))
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка экспорта дистанций: {e}")
    
    def new_config(self):
        """Создание новой конфигурации"""
        self.current_config_name = None
        self.map_processor = MapProcessor()
        self.route_optimizer = RouteOptimizer()
        self.start_point = None
        self.end_point = None
        self.scale_set = False
        self.robot_radius_set = False
        
        self.canvas.delete("all")
        self.info_label.config(text="Новая конфигурация создана. Загрузите карту склада")
        self.update_status()

    def open_config(self):
        """Открытие существующей конфигурации"""
        configs_dir = Path("configs")
        if not configs_dir.exists():
            messagebox.showinfo("Информация", "Нет сохраненных конфигураций")
            return
            
        config_dirs = [d for d in configs_dir.iterdir() if d.is_dir()]
        if not config_dirs:
            messagebox.showinfo("Информация", "Нет сохраненных конфигураций")
            return
            
        # Диалог выбора конфигурации
        dialog = tk.Toplevel(self.root)
        dialog.title("Выбор конфигурации")
        dialog.geometry("400x300")
        
        tk.Label(dialog, text="Выберите конфигурацию:", font=("Arial", 12)).pack(pady=10)
        
        listbox = tk.Listbox(dialog, height=10)
        listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        for config_dir in sorted(config_dirs):
            listbox.insert(tk.END, config_dir.name)
        
        def load_selected():
            selection = listbox.curselection()
            if selection:
                config_name = listbox.get(selection[0])
                self.load_config_by_name(config_name)
                dialog.destroy()
        
        tk.Button(dialog, text="Загрузить", command=load_selected).pack(pady=10)
        
    def save_config(self):
        """Сохранение текущей конфигурации"""
        if not self.current_config_name:
            self.save_config_as()
            return
            
        self.save_config_by_name(self.current_config_name)

    def save_config_as(self):
        """Сохранение конфигурации с новым именем"""
        if not hasattr(self, 'current_map_path'):
            messagebox.showwarning("Предупреждение", "Сначала загрузите карту")
            return
            
        # Предлагаем имя на основе карты
        map_name = Path(self.current_map_path).stem if hasattr(self, 'current_map_path') else "new_config"
        
        name = simpledialog.askstring("Сохранение конфигурации", 
                                    "Введите имя конфигурации:", initialvalue=map_name)
        if name:
            self.save_config_by_name(name)
            self.current_config_name = name

    def load_config_by_name(self, config_name):
        """Загрузка конфигурации по имени"""
        config_path = Path("configs") / config_name / "config.json"
        
        if not config_path.exists():
            messagebox.showerror("Ошибка", f"Конфигурация {config_name} не найдена")
            return
            
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # Загружаем карту
            if config.get('map_path') and Path(config['map_path']).exists():
                self.current_map_path = config['map_path']
                self.map_processor.load_map(config['map_path'])
            else:
                messagebox.showwarning("Предупреждение", f"Файл карты не найден: {config.get('map_path')}")
                return
                
            # Восстанавливаем настройки карты
            self.map_processor.scale = config.get('scale', 0.1)
            self.map_processor.robot_radius_meters = config.get('robot_radius_meters', 0.3)
            self.map_processor._update_robot_radius_pixels()
            
            # Восстанавливаем разметку
            self.map_processor.walls = config.get('walls', [])
            self.map_processor.shelves = config.get('shelves', [])
            self.map_processor._rebuild_grid()
            
            # Загружаем товары
            if config.get('products'):
                self.route_optimizer.products = {}
                self.route_optimizer.placed_products = {}
                self.route_optimizer.access_points = {}
                
                for product_data in config['products']:
                    from route_optimizer import Product
                    product = Product(
                        id=product_data['id'],
                        name=product_data['name'],
                        x=product_data.get('x', -1),
                        y=product_data.get('y', -1),
                        access_x=product_data.get('access_x', -1),
                        access_y=product_data.get('access_y', -1),
                        amount=product_data.get('amount', 0)
                    )
                    self.route_optimizer.products[product.id] = product
                    
                    if product.x >= 0 and product.y >= 0:
                        self.route_optimizer.placed_products[product.id] = (product.x, product.y)
                        
                    if product.access_x >= 0 and product.access_y >= 0:
                        self.route_optimizer.access_points[product.id] = (product.access_x, product.access_y)
            
            # Восстанавливаем точки старт/финиш
            start_point = config.get('start_point')
            end_point = config.get('end_point')
            self.start_point = tuple(start_point) if start_point and len(start_point) == 2 else None
            self.end_point = tuple(end_point) if end_point and len(end_point) == 2 else None
            
            # Устанавливаем флаги
            self.scale_set = config.get('scale_set', False)
            self.robot_radius_set = config.get('robot_radius_set', False)
            self.current_config_name = config_name
            
            self.update_status()
            self.display_map()
            
            # Обновляем информацию
            count = len(self.route_optimizer.products)
            placed = len(self.route_optimizer.placed_products)
            access_count = len(self.route_optimizer.access_points)
            
            info_text = f"Конфигурация '{config_name}' загружена: {count} товаров, {placed} размещено, {access_count} с доступом"
            if self.route_optimizer.has_amount_data():
                with_amount = sum(1 for p in self.route_optimizer.products.values() if p.amount > 0)
                info_text += f", {with_amount} с количеством"
                
            self.info_label.config(text=info_text)
            
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось загрузить конфигурацию: {e}")

    def save_config_by_name(self, config_name):
        """Сохранение конфигурации под указанным именем"""
        if not hasattr(self, 'current_map_path'):
            messagebox.showwarning("Предупреждение", "Нет карты для сохранения")
            return
            
        # Создаем структуру папок
        config_dir = Path("configs") / config_name
        config_dir.mkdir(parents=True, exist_ok=True)
        
        # Создаем output папку для этой конфигурации
        output_dir = Path("output") / config_name
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "routes").mkdir(exist_ok=True)
        
        # Собираем данные о товарах
        products_data = []
        for product in self.route_optimizer.products.values():
            products_data.append({
                'id': product.id,
                'name': product.name,
                'x': product.x,
                'y': product.y,
                'access_x': product.access_x,
                'access_y': product.access_y,
                'amount': product.amount
            })
        
        # Создаем конфигурацию
        config = {
            'name': config_name,
            'map_path': getattr(self, 'current_map_path', ''),
            'scale': self.map_processor.scale,
            'robot_radius_meters': self.map_processor.robot_radius_meters,
            'scale_set': self.scale_set,
            'robot_radius_set': self.robot_radius_set,
            'walls': self.map_processor.walls,
            'shelves': self.map_processor.shelves,
            'products': products_data,
            'start_point': self.start_point,
            'end_point': self.end_point,
            'created': datetime.now().isoformat(),
            'modified': datetime.now().isoformat()
        }
        
        config_path = config_dir / "config.json"
        
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
                
            self.current_config_name = config_name
            messagebox.showinfo("Успех", f"Конфигурация '{config_name}' сохранена")
            
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось сохранить конфигурацию: {e}")

    def auto_save(self):
        """Автосохранение текущей конфигурации"""
        if self.current_config_name and hasattr(self, 'current_map_path'):
            self.save_config_by_name(self.current_config_name)

if __name__ == "__main__":
    root = tk.Tk()
    root.title("Оптимизатор маршрутов склада")
    app = WarehouseGUI(root)
    root.mainloop()