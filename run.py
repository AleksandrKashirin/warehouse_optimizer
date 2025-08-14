#!/usr/bin/env python3
"""
Система оптимизации маршрутов склада
Быстрый запуск и проверка зависимостей
"""

import subprocess
import sys
from pathlib import Path


def check_dependencies():
    """Проверка и установка зависимостей"""
    required = ["numpy", "Pillow"]
    missing = []

    for package in required:
        try:
            __import__(package if package != "Pillow" else "PIL")
        except ImportError:
            missing.append(package)

    if missing:
        print(f"Установка недостающих пакетов: {', '.join(missing)}")
        subprocess.check_call([sys.executable, "-m", "pip", "install"] + missing)


def setup_directories():
    """Создание необходимых директорий"""
    dirs = [Path("data"), Path("data/photos"), Path("output"), Path("output/routes")]

    for dir_path in dirs:
        dir_path.mkdir(exist_ok=True)

    print("✓ Директории созданы")


def generate_test_data():
    """Генерация тестовых данных если нет"""
    products_file = Path("data/products.csv")
    photos_dir = Path("data/photos")

    if not products_file.exists():
        # Создаем базовый файл товаров
        with open(products_file, 'w', encoding='utf-8', newline='') as f:
            import csv
            writer = csv.writer(f)
            writer.writerow(["ID", "Название", "X", "Y", "Access_X", "Access_Y"])
            products = [
                ("A001", "Молоко пастеризованное"),
                ("A002", "Хлеб черный"),
                ("A003", "Масло сливочное"),
                ("A004", "Сыр твердый"),
                ("A005", "Колбаса вареная"),
                ("B001", "Гречка крупа"),
                ("B002", "Рис круглый"),
                ("B003", "Макароны спагетти"),
                ("B004", "Мука пшеничная"),
                ("B005", "Сахар белый"),
            ]
            for product_id, name in products:
                writer.writerow([product_id, name, "", "", "", ""])
        print("✓ Файл с товарами создан")

    # Генерация тестовых фото товаров
    if not any(photos_dir.glob("*.jpg")) and not any(photos_dir.glob("*.png")):
        print("Генерация тестовых фото товаров...")
        try:
            from generate_test_photos import generate_product_photos
            generate_product_photos()
            print("✓ Тестовые фото созданы")
        except:
            print("⚠ Не удалось создать тестовые фото")


def main():
    print("=== Система оптимизации маршрутов склада ===\n")

    print("1. Проверка зависимостей...")
    check_dependencies()

    print("2. Настройка директорий...")
    setup_directories()

    print("3. Подготовка тестовых данных...")
    generate_test_data()

    print("\n4. Запуск системы...")
    print("НОВЫЙ ФУНКЦИОНАЛ:")
    print("- Поддержка PNG/JPG изображений карт")
    print("- Интерактивная разметка стен (клик за кликом, ESC для сохранения)")
    print("- Интерактивная разметка стеллажей (по диагонали)")
    print("- Сохранение/загрузка разметки")
    print()
    
    from main import main as run_app
    run_app()


if __name__ == "__main__":
    main()