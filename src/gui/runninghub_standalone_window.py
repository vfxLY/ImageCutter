import os
import sys
import importlib.util
import cv2
import numpy as np
import requests
import time
import base64
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                           QGroupBox, QFormLayout, QLineEdit, QPushButton, 
                           QMessageBox, QProgressBar, QListWidget, QLabel,
                           QFileDialog, QSplitter)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QIcon

class RunningHubAPI:
    """RunningHub API 核心交互类"""
    def __init__(self, api_key: str, base_url: str = "https://api.runninghub.io/v1"):
        self.api_key = api_key
        self.base_url = base_url
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

    def run_workflow(self, workflow_id: str, image_data: bytes, filename: str) -> str:
        """提交工作流任务"""
        base64_image = base64.b64encode(image_data).decode("utf-8")
        
        payload = {
            "workflow_id": workflow_id,
            "inputs": {
                "image": base64_image,
                "filename": filename
            }
        }
        
        response = requests.post(
            f"{self.base_url}/workflows/run",
            json=payload,
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()["task_id"]

    def get_task_result(self, task_id: str, timeout: int = 60) -> str:
        """获取任务结果"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            response = requests.get(
                f"{self.base_url}/tasks/{task_id}",
                headers=self.headers
            )
            response.raise_for_status()
            task_status = response.json()
            
            if task_status["status"] == "completed":
                return task_status["outputs"].get("image")
            elif task_status["status"] == "failed":
                raise Exception(f"处理失败: {task_status.get('error', '未知错误')}")
            
            time.sleep(2)
        raise TimeoutError("任务超时")


class RunningHubProcessor(QThread):
    """图片处理线程"""
    progress_updated = pyqtSignal(int)
    image_processed = pyqtSignal(str)
    processing_finished = pyqtSignal()
    error_occurred = pyqtSignal(str)

    def __init__(self, api_key, workflow_id, input_paths, output_dir, timeout=60):
        super().__init__()
        self.api = RunningHubAPI(api_key)
        self.workflow_id = workflow_id
        self.input_paths = input_paths
        self.output_dir = output_dir
        self.timeout = timeout
        self._stop_flag = False

    def run(self):
        try:
            os.makedirs(self.output_dir, exist_ok=True)
            total = len(self.input_paths)
            
            for i, input_path in enumerate(self.input_paths):
                if self._stop_flag:
                    self.error_occurred.emit("处理已取消")
                    return
                
                output_path = self._process_single_image(input_path)
                if output_path:
                    self.image_processed.emit(output_path)
                
                progress = int((i + 1) / total * 100)
                self.progress_updated.emit(progress)
            
            self.processing_finished.emit()
            
        except Exception as e:
            self.error_occurred.emit(f"处理错误: {str(e)}")

    def _process_single_image(self, input_path):
        try:
            with open(input_path, "rb") as f:
                image_data = f.read()
            
            filename = os.path.basename(input_path)
            task_id = self.api.run_workflow(self.workflow_id, image_data, filename)
            base64_result = self.api.get_task_result(task_id, self.timeout)
            
            if not base64_result:
                raise Exception("未获取到处理结果")
            
            return self._save_processed_image(base64_result, input_path)
            
        except Exception as e:
            self.error_occurred.emit(f"处理 {filename} 失败: {str(e)}")
            return None

    def _save_processed_image(self, base64_data, original_path):
        image_bytes = base64.b64decode(base64_data)
        nparr = np.frombuffer(image_bytes, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        filename = os.path.basename(original_path)
        name, ext = os.path.splitext(filename)
        output_path = os.path.join(self.output_dir, f"{name}_processed{ext}")
        
        cv2.imwrite(output_path, image)
        return output_path

    def stop_processing(self):
        self._stop_flag = True


class RunningHubStandaloneWindow(QMainWindow):
    """独立的RunningHub图片处理窗口"""
    def __init__(self):
        super().__init__()
        self.image_paths = []
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("RunningHub 图片处理工具")
        self.setGeometry(100, 100, 800, 600)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # 创建分割器
        splitter = QSplitter(Qt.Orientation.Vertical)
        
        # API配置区域
        config_group = QGroupBox("API 配置")
        config_layout = QFormLayout()
        
        self.api_key_edit = QLineEdit()
        self.api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        config_layout.addRow("API Key:", self.api_key_edit)
        
        self.workflow_id_edit = QLineEdit()
        config_layout.addRow("工作流ID:", self.workflow_id_edit)
        
        self.output_dir_edit = QLineEdit()
        browse_btn = QPushButton("浏览")
        browse_btn.clicked.connect(self.browse_output_dir)
        
        output_layout = QHBoxLayout()
        output_layout.addWidget(self.output_dir_edit)
        output_layout.addWidget(browse_btn)
        config_layout.addRow("输出目录:", output_layout)
        
        config_group.setLayout(config_layout)
        splitter.addWidget(config_group)
        
        # 图片列表区域
        list_group = QGroupBox("待处理图片")
        list_layout = QVBoxLayout()
        
        self.image_list = QListWidget()
        self.image_list.setAlternatingRowColors(True)
        list_layout.addWidget(self.image_list)
        
        btn_layout = QHBoxLayout()
        self.add_btn = QPushButton("添加图片")
        self.add_btn.clicked.connect(self.add_images)
        self.clear_btn = QPushButton("清空列表")
        self.clear_btn.clicked.connect(self.clear_list)
        
        btn_layout.addWidget(self.add_btn)
        btn_layout.addWidget(self.clear_btn)
        list_layout.addLayout(btn_layout)
        
        list_group.setLayout(list_layout)
        splitter.addWidget(list_group)
        
        # 控制区域
        control_layout = QVBoxLayout()
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setEnabled(False)
        control_layout.addWidget(self.progress_bar)
        
        self.status_label = QLabel("就绪")
        control_layout.addWidget(self.status_label)
        
        self.process_btn = QPushButton("开始处理")
        self.process_btn.clicked.connect(self.start_processing)
        control_layout.addWidget(self.process_btn)
        
        control_widget = QWidget()
        control_widget.setLayout(control_layout)
        splitter.addWidget(control_widget)
        
        # 设置分割比例
        splitter.setSizes([150, 350, 100])
        main_layout.addWidget(splitter)

    def browse_output_dir(self):
        dir_path = QFileDialog.getExistingDirectory(self, "选择输出目录")
        if dir_path:
            self.output_dir_edit.setText(dir_path)

    def add_images(self):
        file_paths, _ = QFileDialog.getOpenFileNames(
            self, "选择图片", "", 
            "图片文件 (*.png *.jpg *.jpeg *.bmp *.gif)"
        )
        
        if file_paths:
            for path in file_paths:
                if path not in self.image_paths:
                    self.image_paths.append(path)
                    self.image_list.addItem(os.path.basename(path))
            self.status_label.setText(f"已添加 {len(file_paths)} 张图片")

    def clear_list(self):
        self.image_list.clear()
        self.image_paths = []
        self.status_label.setText("列表已清空")

    def start_processing(self):
        api_key = self.api_key_edit.text().strip()
        workflow_id = self.workflow_id_edit.text().strip()
        output_dir = self.output_dir_edit.text().strip()
        
        if not all([api_key, workflow_id, output_dir, self.image_paths]):
            QMessageBox.warning(self, "参数缺失", "请完善所有信息并添加图片")
            return
        
        self.processor = RunningHubProcessor(
            api_key=api_key,
            workflow_id=workflow_id,
            input_paths=self.image_paths,
            output_dir=output_dir
        )
        
        self.processor.progress_updated.connect(self.progress_bar.setValue)
        self.processor.image_processed.connect(self.update_status)
        self.processor.processing_finished.connect(self.process_finished)
        self.processor.error_occurred.connect(self.show_error)
        
        self.progress_bar.setEnabled(True)
        self.process_btn.setEnabled(False)
        self.add_btn.setEnabled(False)
        self.clear_btn.setEnabled(False)
        self.status_label.setText("开始处理...")
        self.processor.start()

    def update_status(self, path):
        self.status_label.setText(f"已完成: {os.path.basename(path)}")

    def process_finished(self):
        self.progress_bar.setValue(100)
        self.status_label.setText("所有图片处理完成")
        self.reset_controls()
        QMessageBox.information(self, "完成", "处理已完成")

    def show_error(self, message):
        self.status_label.setText(f"错误: {message}")
        self.reset_controls()
        QMessageBox.critical(self, "错误", message)

    def reset_controls(self):
        self.progress_bar.setEnabled(False)
        self.process_btn.setEnabled(True)
        self.add_btn.setEnabled(True)
        self.clear_btn.setEnabled(True)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = RunningHubStandaloneWindow()
    window.show()
    sys.exit(app.exec())
