from PyQt6.QtCore import QThread, pyqtSignal
import os
import pathlib
import sys
print(sys.path)

class Model:

    def __init__(self):
        self.model = None
        self.imported = False
    
    def load(self):
        if self.model is None:
            self.__load()

    def __load(self):
        if not self.imported:
            self.imported = True
            import torch
            import sys

        # 获取当前脚本文件所在的目录
        current_dir = os.path.dirname(os.path.abspath(__file__))
        # 计算模型文件相对于当前脚本的相对路径
        # 假设从 src/image_processing 到 src/ai-models/2024-11-00/best.pt 的相对路径是这样
        model_relative_path = os.path.join("..", "ai-models", "2024-11-00", "best.pt")
        # 组合成绝对路径
        model_path = os.path.normpath(os.path.join(current_dir, model_relative_path))

        # Redirect sys.stderr to a file or a valid stream
        if sys.stderr is None:
            sys.stderr = open(os.devnull, 'w')

        temp = pathlib.PosixPath
        pathlib.PosixPath = pathlib.WindowsPath
        self.model = torch.hub.load('ultralytics/yolov5', 'custom', path=model_path)
        pathlib.PosixPath = temp
    
    def __call__(self, *args, **kwds):
        if self.model is None:
            self.__load()
        return self.model(*args, **kwds)

model = Model()