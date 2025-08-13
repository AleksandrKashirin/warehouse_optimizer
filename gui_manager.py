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

        self.setup_ui()

    def setup_ui(self):
        # Панель управления - первая строка
        control_frame1 = tk.Frame(self.root)
        control_frame1.pack(side=tk.TOP, fill=tk.X, padx=5, pady=2)

        tk.Button(control_frame1, text="Загрузить карту", command=self.load_map).pack(
            side=tk.LEFT, padx=2
        )
        tk.Button(
            control_frame1, text="Загрузить товары", command=self.load_products
        ).pack(side=tk.LEFT, padx=2)
        tk.Button(
            control_frame1, text="Установить масштаб", command=self.set_scale_mode
        ).pack(side=tk.LEFT, padx=2)
        tk.Button(
            control_frame1, text="Радиус робота", command=self.set_robot_radius
        ).pack(side=tk.LEFT, padx=2)
        tk.Button(
            control_frame1, text="Разместить товары", command=self.place_products_mode
        ).pack(side=tk.LEFT, padx=2)

        # Панель управления - вторая строка
        control_frame2 = tk.Frame(self.root)
        control_frame2.pack(side=tk.TOP, fill=tk.X, padx=5, pady=2)

        tk.Button(
            control_frame2,
            text="Установить старт/финиш",
            command=self.set_route_points_mode,
        ).pack(side=tk.LEFT, padx=2)
        tk.Button(
            control_frame2, text="Генерировать маршруты", command=self.generate_routes
        ).pack(side=tk.LEFT, padx=2)
        tk.Button(
            control_frame2, text="Сохранить товары", command=self.save_products
        ).pack(side=tk.LEFT, padx=2)
        tk.Button(
            control_frame2, text="Просмотр маршрутов", command=self.view_routes
        ).pack(side=tk.LEFT, padx=2)

        # Информационная панель
        info_frame = tk.Frame(self.root)
        info_frame.pack(side=tk.TOP, fill=tk.X, padx=5)

        self.info_label = tk.Label(
            info_frame, text="Загрузите карту склада", anchor=tk.W
        )
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
        v_scrollbar = tk.Scrollbar(
            canvas_frame, orient=tk.VERTICAL, command=self.canvas.yview
        )
        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        h_scrollbar = tk.Scrollbar(
            self.root, orient=tk.HORIZONTAL, command=self.canvas.xview
        )
        h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)

        self.canvas.config(
            yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set
        )
        self.canvas.bind("<Button-1>", self.on_canvas_click)
        self.canvas.bind("<Motion>", self.on_mouse_move)

        self.update_status()

    def update_status(self):
        """Обновление статусной строки"""
        status_parts = []

        if self.scale_set:
            status_parts.append(f"Масштаб: 1px = {self.map_processor.scale:.2f}м")
        else:
            status_parts.append("Масштаб: не задан")

        if self.robot_radius_set:
            status_parts.append(
                f"Радиус робота: {self.map_processor.robot_radius_meters:.2f}м"
            )
        else:
            status_parts.append("Радиус: не задан")

        self.status_label.config(text=" | ".join(status_parts))

    def load_map(self):
        filepath = filedialog.askopenfilename(
            title="Выберите карту склада",
            filetypes=[("BMP files", "*.bmp"), ("All files", "*.*")],
        )
        if filepath:
            try:
                grid = self.map_processor.load_map(filepath)
                self.display_map()
                self.info_label.config(
                    text=f"Карта загружена: {self.map_processor.width}x{self.map_processor.height} пикселей"
                )
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось загрузить карту: {e}")

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
            text="Кликайте на СТЕЛЛАЖИ (черные области) или рядом с ними",
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
        tk.Button(button_frame, text="Выбрать", command=on_select).pack(
            side=tk.LEFT, padx=5
        )
        tk.Button(button_frame, text="Завершить", command=on_cancel).pack(
            side=tk.LEFT, padx=5
        )

    def set_route_points_mode(self):
        self.mode = "route_points"
        # Очищаем предыдущие точки
        self.start_point = None
        self.end_point = None
        self.canvas.delete("route_point")
        self.display_map()
        self.info_label.config(
            text="Кликните в ПРОХОДЕ (белая область) для установки точки СТАРТА"
        )

    def on_canvas_click(self, event):
        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)

        if self.mode == "scale":
            self.scale_points.append((x, y))
            self.canvas.create_oval(
                x - 3, y - 3, x + 3, y + 3, fill="red", tags="scale"
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

        elif self.mode == "place" and hasattr(self, "selected_product_id"):
            ix, iy = int(x), int(y)

            # Если клик на стеллаже - размещаем товар там
            if self.map_processor.is_shelf(ix, iy):
                # Ищем точку доступа с увеличенным радиусом
                access = self.map_processor.find_nearest_walkable(ix, iy, max_radius=50)
                if access:
                    self.route_optimizer.place_product(self.selected_product_id, ix, iy, access)
                    self.display_map()
                    self.info_label.config(text=f"Товар размещен на стеллаже с точкой доступа")
                    self.show_product_selector()
                else:
                    messagebox.showwarning("Внимание", "К этому месту нет доступа!")
            # Если клик в проходе рядом со стеллажом - ищем ближайший стеллаж
            else:
                # Ищем ближайший стеллаж в радиусе 50 пикселей
                found = False
                for r in range(1, 50):
                    for dx in range(-r, r + 1):
                        for dy in range(-r, r + 1):
                            sx, sy = ix + dx, iy + dy
                            if self.map_processor.is_shelf(sx, sy):
                                # Ищем точку доступа с увеличенным радиусом
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
                    messagebox.showwarning("Внимание", "Кликните ближе к стеллажу (черная область)")

        elif self.mode == "route_points":
            ix, iy = int(x), int(y)

            if not self.start_point:
                # Проверка с меньшим радиусом для большей гибкости
                if self.map_processor.is_walkable(ix, iy, check_radius=False):
                    self.start_point = (ix, iy)
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
            elif self.mode == "place":
                status = "стеллаж" if self.map_processor.is_shelf(ix, iy) else "проход"
                self.info_label.config(
                    text=f"({ix}, {iy}) - {status} | Кликните для размещения товара"
                )
            elif self.mode == "route_points":
                walkable = (
                    "можно"
                    if self.map_processor.is_walkable(ix, iy, check_radius=False)
                    else "нельзя"
                )
                self.info_label.config(
                    text=f"({ix}, {iy}) - {walkable} установить точку"
                )

    def display_map(self):
        if self.map_processor.grid is None:
            return

        # Создание изображения из сетки
        img_array = (1 - self.map_processor.grid) * 255
        img = Image.fromarray(img_array.astype(np.uint8), mode="L")
        img = img.convert("RGB")

        draw = ImageDraw.Draw(img)

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

        # Отрисовка размещенных товаров
        for product_id, (x, y) in self.route_optimizer.placed_products.items():
            # Товар на стеллаже
            if product_id in self.route_optimizer.access_points:
                draw.ellipse([x - 3, y - 3, x + 3, y + 3], fill="yellow", outline="orange")
                # Показываем точку доступа
                access_x, access_y = self.route_optimizer.access_points[product_id]
                draw.ellipse([access_x - 2, access_y - 2, access_x + 2, access_y + 2], fill="lightgreen", outline="green")
                draw.line([x, y, access_x, access_y], fill="lightblue", width=1)
            else:
                # Товар без точки доступа
                draw.ellipse([x - 3, y - 3, x + 3, y + 3], fill="orange", outline="red")
            
            draw.text((x + 5, y - 5), product_id, fill="blue")

        self.map_image = img
        self.photo_image = ImageTk.PhotoImage(img)

        self.canvas.delete("all")
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.photo_image)
        self.canvas.config(scrollregion=self.canvas.bbox("all"))

    def generate_routes(self):
        # Проверка настроек
        if not self.scale_set:
            messagebox.showwarning(
                "Предупреждение", "Сначала установите масштаб карты!"
            )
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

        # Используем товары с точками доступа
        access_count = len(self.route_optimizer.access_points)
        if access_count < 5:
            messagebox.showwarning("Предупреждение", f"Разместите минимум 5 товаров с точками доступа. Сейчас: {access_count}")
            return

        num_samples = simpledialog.askinteger(
            "Генерация", "Количество выборок:", initialvalue=10
        )
        if not num_samples:
            return

        try:
            samples = self.route_optimizer.generate_samples(num_samples)

            progress = tk.Toplevel(self.root)
            progress.title("Генерация маршрутов")
            progress_label = tk.Label(progress, text="Инициализация...")
            progress_label.pack(padx=20, pady=10)
            progress_bar = ttk.Progressbar(
                progress, length=300, mode="determinate", maximum=num_samples
            )
            progress_bar.pack(padx=20, pady=10)

            successful_routes = 0
            failed_routes = 0

            for i, sample in enumerate(samples):
                progress_label.config(text=f"Обработка маршрута {i+1}/{num_samples}")
                progress.update()

                # Используем сохраненные точки доступа
                coords = self.route_optimizer.get_access_coordinates(sample)

                if len(coords) != len(sample):
                    failed_routes += 1
                    progress_bar["value"] = i + 1
                    progress.update()
                    print(f"Маршрут {i+1}: не все товары имеют точки доступа")
                    continue

                # Используем упрощенный алгоритм для поиска маршрута
                path, distance, order = self.map_processor.find_optimal_route_simple(
                    self.start_point, coords, self.end_point
                )

                if path and len(path) > 0:
                    # Переупорядочиваем sample согласно оптимальному порядку
                    if order:
                        ordered_sample = [sample[idx] for idx in order]
                    else:
                        ordered_sample = sample

                    self.save_route_image(i + 1, path, ordered_sample, distance)
                    self.route_optimizer.save_route_info(
                        i + 1, ordered_sample, distance, path
                    )
                    successful_routes += 1
                    print(f"Маршрут {i+1}: успешно, {distance:.2f} м")
                else:
                    failed_routes += 1
                    print(f"Маршрут {i+1}: не удалось построить")

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
            import traceback

            traceback.print_exc()

    def save_route_image(
        self, route_id: int, path: List[tuple], products: List[str], distance: float
    ):
        if not self.map_image:
            return

        Path("output/routes").mkdir(parents=True, exist_ok=True)

        # Создаем увеличенное изображение для размещения информации
        map_width, map_height = self.map_image.size
        info_width = 400
        final_width = map_width + info_width
        final_height = max(map_height, 600)

        final_img = Image.new("RGB", (final_width, final_height), "white")

        # Копируем карту с маршрутом
        route_img = self.map_image.copy()
        draw_route = ImageDraw.Draw(route_img)

        # Рисование пути
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
                
                # Линия к товару
                if product_id in self.route_optimizer.placed_products:
                    x, y = self.route_optimizer.placed_products[product_id]
                    draw_route.line([ax, ay, x, y], fill="orange", width=1)
                    draw_route.ellipse([x - 4, y - 4, x + 4, y + 4], fill="yellow", outline="red")

        # Отметка старта и финиша
        if self.start_point:
            x, y = self.start_point
            draw_route.ellipse(
                [x - 6, y - 6, x + 6, y + 6], fill="green", outline="darkgreen", width=2
            )
            draw_route.text((x + 8, y - 8), "START", fill="green")

        if self.end_point:
            x, y = self.end_point
            draw_route.ellipse(
                [x - 6, y - 6, x + 6, y + 6], fill="red", outline="darkred", width=2
            )
            draw_route.text((x + 8, y - 8), "FINISH", fill="red")

        final_img.paste(route_img, (0, 0))

        # Информационная панель
        draw = ImageDraw.Draw(final_img)

        try:
            font_title = ImageFont.truetype("arial.ttf", 16)
            font_normal = ImageFont.truetype("arial.ttf", 12)
        except:
            font_title = ImageFont.load_default()
            font_normal = ImageFont.load_default()

        info_x = map_width + 10
        y_pos = 10

        draw.text(
            (info_x, y_pos), f"МАРШРУТ #{route_id}", fill="black", font=font_title
        )
        y_pos += 30

        draw.line([(info_x, y_pos), (final_width - 10, y_pos)], fill="gray", width=1)
        y_pos += 10

        draw.text(
            (info_x, y_pos),
            f"Расстояние: {distance:.2f} м",
            fill="black",
            font=font_normal,
        )
        y_pos += 20
        draw.text(
            (info_x, y_pos), f"Точек пути: {len(path)}", fill="black", font=font_normal
        )
        y_pos += 20
        draw.text(
            (info_x, y_pos), f"Товаров: {len(products)}", fill="black", font=font_normal
        )
        y_pos += 30

        draw.line([(info_x, y_pos), (final_width - 10, y_pos)], fill="gray", width=1)
        y_pos += 10

        draw.text((info_x, y_pos), "ТОВАРЫ ДЛЯ СБОРА:", fill="black", font=font_title)
        y_pos += 25

        # Список товаров с фото
        for idx, product_id in enumerate(products, 1):
            if product_id in self.route_optimizer.products:
                product = self.route_optimizer.products[product_id]

                draw.text(
                    (info_x, y_pos),
                    f"{idx}. {product.id}",
                    fill="black",
                    font=font_normal,
                )
                y_pos += 18
                draw.text(
                    (info_x + 20, y_pos),
                    f"{product.name}",
                    fill="gray",
                    font=font_normal,
                )
                y_pos += 18

                # Фото товара
                photo_path = f"data/photos/{product.id}.jpg"
                if not Path(photo_path).exists():
                    photo_path = f"data/photos/{product.id}.png"

                if Path(photo_path).exists():
                    try:
                        product_img = Image.open(photo_path)
                        product_img.thumbnail((60, 60), Image.Resampling.LANCZOS)
                        final_img.paste(product_img, (info_x + 20, y_pos))
                        y_pos += 65
                    except:
                        y_pos += 5
                else:
                    draw.rectangle(
                        [(info_x + 20, y_pos), (info_x + 80, y_pos + 60)],
                        outline="gray",
                        width=1,
                    )
                    draw.text((info_x + 35, y_pos + 25), "Нет\nфото", fill="gray")
                    y_pos += 65

                y_pos += 10

                if y_pos > final_height - 50:
                    draw.text((info_x, y_pos), "...", fill="gray")
                    break

        from datetime import datetime

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        draw.text(
            (info_x, final_height - 30),
            f"Создано: {timestamp}",
            fill="gray",
            font=font_normal,
        )

        filepath = f"output/routes/route_{route_id}.png"
        final_img.save(filepath)
        print(f"Изображение маршрута сохранено: {filepath}")

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

        tk.Label(
            list_frame, text="Сохраненные маршруты:", font=("Arial", 12, "bold")
        ).pack()

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
                info_text.insert(
                    tk.END, f"Расстояние: {route['distance_meters']:.2f} м\n"
                )
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
                image_path = f"output/routes/route_{route_id}.png"
                if Path(image_path).exists():
                    import os

                    if os.name == "nt":
                        os.startfile(image_path)
                    else:
                        os.system(
                            f"open '{image_path}' 2>/dev/null || xdg-open '{image_path}'"
                        )
                else:
                    messagebox.showwarning(
                        "Внимание", "Изображение маршрута не найдено"
                    )

        listbox.bind("<<ListboxSelect>>", on_select)

        tk.Button(list_frame, text="Открыть изображение", command=open_image).pack(
            pady=5
        )
        tk.Button(viewer, text="Закрыть", command=viewer.destroy).pack(
            side=tk.BOTTOM, pady=10
        )


if __name__ == "__main__":
    root = tk.Tk()
    root.title("Оптимизатор маршрутов склада")
    app = WarehouseGUI(root)
    root.mainloop()