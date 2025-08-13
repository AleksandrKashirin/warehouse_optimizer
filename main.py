import os
import sys
import tkinter as tk
from pathlib import Path

from gui_manager import WarehouseGUI


def main():
    # Создание необходимых директорий
    Path("data").mkdir(exist_ok=True)
    Path("data/photos").mkdir(exist_ok=True)
    Path("output").mkdir(exist_ok=True)
    Path("output/routes").mkdir(exist_ok=True)

    root = tk.Tk()
    root.title("Оптимизатор маршрутов склада")

    app = WarehouseGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
