import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageDraw, ImageTk
import numpy as np


class MapEditor:
    def __init__(self, parent):
        self.window = tk.Toplevel(parent)
        self.window.title("Редактор карты")
        self.window.geometry("900x700")
        
        self.original_image = None
        self.edit_image = None
        self.photo_image = None
        self.drawing = False
        self.last_x = None
        self.last_y = None
        
        # Режимы рисования
        self.draw_mode = "wall"  # wall, shelf, floor, eraser
        self.brush_size = 5
        
        self.setup_ui()
        
    def setup_ui(self):
        # Панель инструментов
        toolbar = tk.Frame(self.window)
        toolbar.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        
        # Режимы
        tk.Label(toolbar, text="Инструмент:").pack(side=tk.LEFT, padx=5)
        
        self.mode_var = tk.StringVar(value="wall")
        modes = [
            ("Стена", "wall", "black"),
            ("Стеллаж", "shelf", "gray"), 
            ("Пол", "floor", "white"),
            ("Ластик", "eraser", "white")
        ]
        
        for text, mode, color in modes:
            btn = tk.Radiobutton(toolbar, text=text, variable=self.mode_var, 
                                value=mode, command=lambda m=mode: self.set_mode(m))
            btn.pack(side=tk.LEFT, padx=2)
        
        tk.Label(toolbar, text="  Размер:").pack(side=tk.LEFT, padx=5)
        self.size_var = tk.IntVar(value=5)
        size_spin = tk.Spinbox(toolbar, from_=1, to=50, textvariable=self.size_var,
                               width=5, command=self.update_brush_size)
        size_spin.pack(side=tk.LEFT)
        
        # Кнопки действий
        tk.Button(toolbar, text="Очистить", command=self.clear_all).pack(side=tk.LEFT, padx=10)
        tk.Button(toolbar, text="Инверт", command=self.invert).pack(side=tk.LEFT, padx=2)
        tk.Button(toolbar, text="Сохранить BMP", command=self.save_bmp, 
                 bg="green", fg="white").pack(side=tk.RIGHT, padx=5)
        
        # Информация
        self.info_label = tk.Label(toolbar, text="")
        self.info_label.pack(side=tk.RIGHT, padx=10)
        
        # Холст
        canvas_frame = tk.Frame(self.window)
        canvas_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.canvas = tk.Canvas(canvas_frame, bg="gray")
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Скроллбары
        v_scroll = tk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        v_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        h_scroll = tk.Scrollbar(self.window, orient=tk.HORIZONTAL, command=self.canvas.xview)
        h_scroll.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.canvas.config(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)
        
        # События мыши
        self.canvas.bind("<Button-1>", self.start_draw)
        self.canvas.bind("<B1-Motion>", self.draw)
        self.canvas.bind("<ButtonRelease-1>", self.stop_draw)
        self.canvas.bind("<Motion>", self.on_mouse_move)
        
    def load_image(self, filepath):
        """Загрузка изображения для редактирования"""
        self.original_image = Image.open(filepath).convert('RGB')
        self.edit_image = self.original_image.copy()
        self.display_image()
        self.info_label.config(text=f"Размер: {self.edit_image.size}")
        
    def set_mode(self, mode):
        self.draw_mode = mode
        
    def update_brush_size(self):
        self.brush_size = self.size_var.get()
        
    def get_draw_color(self):
        """Получение цвета для текущего режима"""
        if self.draw_mode == "wall":
            return (0, 0, 0)  # Черный
        elif self.draw_mode == "shelf":
            return (64, 64, 64)  # Темно-серый
        elif self.draw_mode in ["floor", "eraser"]:
            return (255, 255, 255)  # Белый
        return (255, 255, 255)
        
    def start_draw(self, event):
        self.drawing = True
        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)
        self.last_x = x
        self.last_y = y
        self.draw_point(x, y)
        
    def draw(self, event):
        if self.drawing and self.edit_image:
            x = self.canvas.canvasx(event.x)
            y = self.canvas.canvasy(event.y)
            
            # Рисуем линию от последней точки
            if self.last_x and self.last_y:
                self.draw_line(self.last_x, self.last_y, x, y)
            
            self.last_x = x
            self.last_y = y
            self.display_image()
            
    def draw_point(self, x, y):
        """Рисование точки"""
        if not self.edit_image:
            return
            
        draw = ImageDraw.Draw(self.edit_image)
        color = self.get_draw_color()
        r = self.brush_size
        
        # Круглая кисть
        draw.ellipse([x-r, y-r, x+r, y+r], fill=color, outline=color)
        
    def draw_line(self, x1, y1, x2, y2):
        """Рисование линии между точками"""
        if not self.edit_image:
            return
            
        draw = ImageDraw.Draw(self.edit_image)
        color = self.get_draw_color()
        
        # Толстая линия
        draw.line([x1, y1, x2, y2], fill=color, width=self.brush_size*2)
        
        # Закругления на концах
        r = self.brush_size
        draw.ellipse([x1-r, y1-r, x1+r, y1+r], fill=color)
        draw.ellipse([x2-r, y2-r, x2+r, y2+r], fill=color)
        
    def stop_draw(self, event):
        self.drawing = False
        self.last_x = None
        self.last_y = None
        
    def on_mouse_move(self, event):
        x = int(self.canvas.canvasx(event.x))
        y = int(self.canvas.canvasy(event.y))
        
        if self.edit_image and 0 <= x < self.edit_image.width and 0 <= y < self.edit_image.height:
            pixel = self.edit_image.getpixel((x, y))
            
            if pixel == (0, 0, 0):
                pixel_type = "Стена"
            elif pixel == (64, 64, 64):
                pixel_type = "Стеллаж"
            elif pixel == (255, 255, 255):
                pixel_type = "Пол"
            else:
                pixel_type = "Другое"
                
            self.info_label.config(text=f"({x}, {y}) - {pixel_type}")
            
    def clear_all(self):
        """Очистка всей карты"""
        if self.edit_image:
            self.edit_image = Image.new('RGB', self.edit_image.size, (255, 255, 255))
            self.display_image()
            
    def invert(self):
        """Инвертирование карты"""
        if self.edit_image:
            arr = np.array(self.edit_image)
            # Меняем черное на белое и наоборот
            inverted = np.where(arr < 128, 255, 0)
            self.edit_image = Image.fromarray(inverted.astype(np.uint8))
            self.display_image()
            
    def display_image(self):
        """Отображение изображения на холсте"""
        if self.edit_image:
            self.photo_image = ImageTk.PhotoImage(self.edit_image)
            self.canvas.delete("all")
            self.canvas.create_image(0, 0, anchor=tk.NW, image=self.photo_image)
            self.canvas.config(scrollregion=self.canvas.bbox("all"))
            
    def save_bmp(self):
        """Сохранение в BMP формат"""
        if not self.edit_image:
            return
            
        from tkinter import filedialog, messagebox
        
        filepath = filedialog.asksaveasfilename(
            title="Сохранить карту",
            defaultextension=".bmp",
            filetypes=[("BMP files", "*.bmp")]
        )
        
        if filepath:
            # Преобразуем в черно-белое изображение
            gray = self.edit_image.convert('L')
            # Применяем порог: темное -> черное (препятствие), светлое -> белое (проход)
            bw = gray.point(lambda x: 0 if x < 128 else 255, 'L')
            bw.save(filepath)
            messagebox.showinfo("Успех", f"Карта сохранена: {filepath}")
            self.window.destroy()