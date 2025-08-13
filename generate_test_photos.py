import csv
import random
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

def generate_product_photos():
    """Генерация простых тестовых фото товаров"""
    
    photos_dir = Path("data/photos")
    photos_dir.mkdir(parents=True, exist_ok=True)
    
    # Читаем товары
    products_file = Path("data/products.csv") 
    if not products_file.exists():
        print("Файл data/products.csv не найден")
        return
    
    colors = [
        "#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4", "#FFEAA7",
        "#DDA0DD", "#98D8C8", "#F7DC6F", "#BB8FCE", "#85C1E9"
    ]
    
    with open(products_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            product_id = row['ID']
            product_name = row['Название']
            
            # Создаем изображение 100x100
            img = Image.new('RGB', (100, 100), random.choice(colors))
            draw = ImageDraw.Draw(img)
            
            # Рамка
            draw.rectangle([2, 2, 97, 97], outline='black', width=2)
            
            # ID товара
            try:
                font = ImageFont.truetype("arial.ttf", 12)
            except:
                font = ImageFont.load_default()
            
            # Разбиваем название на строки
            lines = product_name.split()
            if len(lines) > 2:
                lines = [' '.join(lines[:2]), ' '.join(lines[2:])]
            
            y_pos = 20
            draw.text((10, y_pos), product_id, fill='black', font=font)
            y_pos += 15
            
            for line in lines:
                if len(line) > 12:
                    line = line[:12] + "..."
                draw.text((10, y_pos), line, fill='black', font=font)
                y_pos += 12
                if y_pos > 70:
                    break
            
            # Сохраняем
            filepath = photos_dir / f"{product_id}.jpg"
            img.save(filepath, 'JPEG')
    
    print(f"Сгенерированы фото товаров в {photos_dir}")

if __name__ == "__main__":
    generate_product_photos()