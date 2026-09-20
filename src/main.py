import os
import sys
from PyQt6.QtCore import QCoreApplication

# 当程序被打包为单文件时，获取临时解压目录
if getattr(sys, 'frozen', False):
    # Nuitka 单文件模式下，会将数据解压到临时目录
    base_dir = sys._MEIPASS  # 这是 Nuitka 自动设置的临时目录变量
else:
    base_dir = os.path.dirname(os.path.abspath(__file__))

# 设置 Qt 插件路径（指向包含 platforms 的目录）
qt_plugins_path = os.path.join(base_dir, "platforms")
QCoreApplication.addLibraryPath(qt_plugins_path)


import sys
import os
import argparse
from PyQt6.QtWidgets import QApplication
from gui.base_window import MainWindow
from gui.splash_screen import SplashScreen
from image_processing.panel import extract_panels_for_image, extract_panels_for_images_in_folder


def start_main_window():
    main_window = MainWindow()
    main_window.show()


def start_splash_screen():
    splash_screen = SplashScreen()
    splash_screen.show()
    splash_screen.closeEvent = lambda _: start_main_window()


def start_gui():
    app = QApplication(sys.argv)
    start_splash_screen()
    sys.exit(app.exec())


def make_parser() -> argparse.ArgumentParser:
    """
    Create the argument parser
    """
    parser = argparse.ArgumentParser(description="Extract panels from manga pages")
    
    parser.add_argument("input_dir", type=str, nargs="?", help="Input directory")
    parser.add_argument("output_dir", type=str, nargs="?", help="Output directory")
    parser.add_argument("-s", "--split-joint-panels", action="store_true", help="Split joint panels")
    parser.add_argument("-f", "--fallback", action="store_true", help="Fallback to a more aggressive method if the first one fails")
    parser.add_argument("-g", "--gui", action="store_true", help="Use GUI")
    parser.add_argument("-v", "--version", action="version", version="Manga-Panel-Extractor v1.1.1")
    
    return parser


def handle_parameters(parser: argparse.ArgumentParser) -> None:
    """
    Handle the parameters passed to the program
    """
    args = parser.parse_args()

    if len(sys.argv) == 1 or args.gui:
        start_gui()
    elif args.input_dir:
        if args.output_dir:
            extract_panels_for_images_in_folder(args.input_dir, args.output_dir, args.fallback, args.split_joint_panels)
        else:
            extract_panels_for_image(args.input_dir, os.path.dirname(args.input_dir), args.fallback, args.split_joint_panels)
    else:
        print("Invalid arguments")
        parser.print_help()


def main():
    parser = make_parser()
    handle_parameters(parser)        


if __name__ == "__main__":
    main()