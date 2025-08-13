import numpy as np
from PIL import Image, ImageDraw


def generate_warehouse_map(width=600, height=400, filename="data/warehouse_map.bmp"):
    """Генерация простой карты склада для тестирования"""

    # Белый фон (проходимая область)
    img = Image.new("L", (width, height), 255)
    draw = ImageDraw.Draw(img)

    # Внешние стены (черные)
    wall_width = 5
    draw.rectangle([0, 0, width - 1, wall_width], fill=0)  # верх
    draw.rectangle([0, height - wall_width, width - 1, height - 1], fill=0)  # низ
    draw.rectangle([0, 0, wall_width, height - 1], fill=0)  # лево
    draw.rectangle([width - wall_width, 0, width - 1, height - 1], fill=0)  # право

    # Стеллажи (черные прямоугольники)
    shelf_width = 40
    shelf_height = 100
    shelf_spacing = 80

    # Ряды стеллажей
    for row in range(3):
        for col in range(4):
            x = 50 + col * (shelf_width + shelf_spacing)
            y = 50 + row * (shelf_height + 30)

            if x + shelf_width < width - 50 and y + shelf_height < height - 50:
                draw.rectangle([x, y, x + shelf_width, y + shelf_height], fill=0)

    img.save(filename)
    print(f"Тестовая карта сохранена: {filename}")


if __name__ == "__main__":
    generate_warehouse_map()
