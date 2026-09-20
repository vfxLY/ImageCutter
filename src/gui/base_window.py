import os
import sys
import subprocess
import time
from PyQt6.QtWidgets import QLineEdit
from PyQt6.QtWidgets import (
    QMainWindow, QFileDialog, QPushButton, QVBoxLayout, QHBoxLayout,
    QWidget, QLabel, QDialog, QListWidget, QScrollArea, QSplitter,
    QApplication, QListWidgetItem, QGridLayout, QCheckBox, QMessageBox,
    QMenu, QToolBar, QInputDialog, QColorDialog, QSpinBox, QGroupBox,
    QComboBox, QProgressBar, QStatusBar
)
from PyQt6 import QtCore, QtGui
from PyQt6.QtGui import QAction, QPixmap, QPainter, QPen, QColor, QCursor
from myutils.myutils import get_file_names, supported_types
from gui.extractor import ExtractionThread
from gui.base_window_ui import Ui_MainWindow
from myutils.respath import resource_path

# 导入RunningHub独立窗口
#from gui.runninghub_standalone_window import RunningHubStandaloneWindow


# 优化后的图像查看窗口（默认自适应窗口）
class ImageViewerWindow(QMainWindow):
    # 新增信号，用于通知图片变更
    image_changed = QtCore.pyqtSignal(int)  # 发送当前图片索引

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("W/S 上下切换画面 | 滚轮缩放 | 中键平移画面")
        self.resize(1000, 600)

        # 核心设置：默认启用自动适应窗口
        self.auto_adjust_window = True  # 窗口大小变化时自动适应
        self.auto_fit_on_load = True    # 加载图片时自动适应窗口

        # 中心部件和滚动区域
        self.scroll_area = QScrollArea()
        self.scroll_area.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll_area.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll_area.setWidgetResizable(True)

        # 图片容器（确保居中）
        self.image_container = QWidget()
        self.container_layout = QVBoxLayout(self.image_container)
        self.container_layout.setContentsMargins(0, 0, 0, 0)
        self.container_layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        # 自定义图片标签，用于处理鼠标事件和显示裁切框
        self.image_label = CustomImageLabel(self)
        self.image_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.container_layout.addWidget(self.image_label)

        self.scroll_area.setWidget(self.image_container)
        self.setCentralWidget(self.scroll_area)

        # 图片区域直接接管滚轮缩放和中键平移，避免事件被滚动区域吞掉。
        self.scroll_area.viewport().installEventFilter(self)
        self.image_label.installEventFilter(self)

        # 图片相关变量
        self.current_pixmap = None  # 当前显示的缩放后图片
        self.original_pixmap = None  # 原始高分辨率图片（不缩放）
        self.current_scale = 1.0  # 当前缩放比例（相对于原始图像）
        self.image_paths = []  # 所有图片的完整路径列表
        self.current_index = -1  # 当前显示图片的索引
        self.scale_history = {}  # 记录每张图片的缩放历史
        self.is_panning = False
        self.pan_last_global_pos = QtCore.QPoint()

        # 裁切相关变量
        self.crop_mode = False  # 是否处于裁切模式
        self.crop_rects = []  # 存储所有裁切框
        self.current_crop_rect = None  # 当前正在绘制的裁切框
        self.drawing = False  # 是否正在绘制
        self.start_point = QtCore.QPoint()  # 绘制起始点
        self.end_point = QtCore.QPoint()  # 绘制结束点

        # 操作历史记录
        self.crop_history = []  # 操作历史栈
        self.history_index = -1  # 当前历史位置

        # 裁切配置
        self.crop_color = QColor(255, 0, 0, 100)  # 裁切框颜色（半透明红色）
        self.crop_line_width = 2  # 裁切框线条宽度

        # 创建工具栏
        self.create_toolbar()

        # 启用右键菜单
        self.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)

        # 创建右键菜单
        self.context_menu = QMenu(self)

        # 右键菜单项
        self.select_image_action = QAction("选中图片", self)
        self.select_image_action.triggered.connect(self.select_current_image)
        self.context_menu.addAction(self.select_image_action)

        self.copy_path_action = QAction("复制图片路径", self)
        self.copy_path_action.triggered.connect(self.copy_image_path)
        self.context_menu.addAction(self.copy_path_action)

        self.open_in_explorer_action = QAction("在资源管理器中打开", self)
        self.open_in_explorer_action.triggered.connect(self.open_in_explorer)
        self.context_menu.addAction(self.open_in_explorer_action)

        # 分隔线
        self.context_menu.addSeparator()

        # 裁切相关菜单项
        self.toggle_crop_action = QAction("启用裁切模式", self)
        self.toggle_crop_action.triggered.connect(self.toggle_crop_mode)
        self.context_menu.addAction(self.toggle_crop_action)

        self.context_clear_crops_action = QAction("清除所有裁切框", self)
        self.context_clear_crops_action.triggered.connect(self.clear_crop_rects)
        self.context_menu.addAction(self.context_clear_crops_action)

        self.context_save_crops_action = QAction("保存所有裁切", self)
        self.context_save_crops_action.triggered.connect(self.save_all_crops)
        self.context_menu.addAction(self.context_save_crops_action)

    def create_toolbar(self):
        """创建工具栏，包含裁切工具"""
        toolbar = QToolBar("工具", self)
        self.addToolBar(toolbar)

        # 放大按钮
        zoom_in_action = QAction("放大", self)
        zoom_in_action.triggered.connect(self.zoom_in)
        toolbar.addAction(zoom_in_action)

        # 缩小按钮
        zoom_out_action = QAction("缩小", self)
        zoom_out_action.triggered.connect(self.zoom_out)
        toolbar.addAction(zoom_out_action)

        # 适应窗口按钮
        fit_window_action = QAction("适应窗口", self)
        fit_window_action.triggered.connect(self.adjust_image_to_window)
        toolbar.addAction(fit_window_action)

        # 分隔符
        toolbar.addSeparator()

        # 裁切模式按钮
        self.crop_mode_action = QAction("启用裁切模式", self)
        self.crop_mode_action.setCheckable(True)
        self.crop_mode_action.triggered.connect(self.toggle_crop_mode)
        toolbar.addAction(self.crop_mode_action)

        # 工具栏的清除裁切框按钮
        self.clear_crops_action = QAction("清除所有裁切框", self)
        self.clear_crops_action.triggered.connect(self.clear_crop_rects)
        self.clear_crops_action.setEnabled(False)
        toolbar.addAction(self.clear_crops_action)

        # 工具栏的保存裁切按钮
        self.save_crops_action = QAction("保存所有裁切", self)
        self.save_crops_action.triggered.connect(self.save_all_crops)
        self.save_crops_action.setEnabled(False)
        toolbar.addAction(self.save_crops_action)

        # 撤销按钮
        self.undo_action = QAction("撤销 (Ctrl+Z)", self)
        self.undo_action.triggered.connect(self.undo_last_crop)
        self.undo_action.setEnabled(False)
        toolbar.addAction(self.undo_action)

        # 分隔符
        toolbar.addSeparator()

        # 配置按钮
        config_action = QAction("裁切设置", self)
        config_action.triggered.connect(self.show_crop_settings)
        toolbar.addAction(config_action)

    def set_image_list(self, image_paths, current_index):
        """设置图片路径列表和当前索引"""
        self.image_paths = image_paths
        self.current_index = current_index
        if 0 <= self.current_index < len(self.image_paths):
            self.load_image_by_index(self.current_index)

    def load_image_by_index(self, index):
        """根据索引加载图片（默认自适应窗口）"""
        if 0 <= index < len(self.image_paths):
            image_path = self.image_paths[index]
            self.original_pixmap = QtGui.QPixmap(image_path)
            if not self.original_pixmap.isNull():
                # 优先使用历史缩放比例，否则默认自适应
                if image_path in self.scale_history:
                    self.current_scale = self.scale_history[image_path]
                    self.auto_fit_on_load = False  # 有历史记录则不自动适应
                else:
                    self.auto_fit_on_load = True   # 首次加载自动适应

                self.update_displayed_image()

                # 首次加载或用户未手动缩放时，自动适应窗口
                if self.auto_fit_on_load:
                    self.adjust_image_to_window()
                    # 保存自适应后的比例到历史记录
                    self.scale_history[image_path] = self.current_scale

                # 更新状态栏
                file_name = os.path.basename(image_path)
                self.set_status(
                    f"图片 {index + 1}/{len(self.image_paths)}: {file_name}  "
                    f"({self.original_pixmap.width()}x{self.original_pixmap.height()})"
                )
                self.image_changed.emit(index)

                # 重置裁切相关状态
                self.select_current_image()
                self.clear_crop_rects()
                self.reset_history()

                return True
        return False

    def reset_history(self):
        """重置操作历史"""
        self.crop_history = []
        self.history_index = -1
        self.update_history_buttons()

    def set_image(self, pixmap):
        """设置单张图片（保持兼容）"""
        self.original_pixmap = pixmap
        self.current_scale = 1.0
        self.update_displayed_image()
        if self.auto_fit_on_load:
            self.adjust_image_to_window()
        self.set_status(f"图像尺寸: {pixmap.width()}x{pixmap.height()}")

    def update_displayed_image(self):
        """基于原始图像和当前缩放比例更新显示"""
        if self.original_pixmap and not self.original_pixmap.isNull():
            scaled_width = int(self.original_pixmap.width() * self.current_scale)
            scaled_height = int(self.original_pixmap.height() * self.current_scale)
            self.current_pixmap = self.original_pixmap.scaled(
                scaled_width, scaled_height,
                QtCore.Qt.AspectRatioMode.KeepAspectRatio,
                QtCore.Qt.TransformationMode.SmoothTransformation
            )
            self.image_label.setPixmap(self.current_pixmap)
            self.image_label.update()

    def get_display_scale(self):
        """返回显示图像相对于原图的实际缩放比例。"""
        if not self.original_pixmap or not self.current_pixmap:
            return 1.0
        if self.original_pixmap.width() == 0:
            return 1.0
        return self.current_pixmap.width() / self.original_pixmap.width()

    def display_rect_to_original(self, display_rect):
        """将显示坐标中的裁切框转换为原图坐标并限制在图像范围内。"""
        scale = self.get_display_scale()
        left = round(display_rect.x() / scale)
        top = round(display_rect.y() / scale)
        right = round((display_rect.x() + display_rect.width()) / scale)
        bottom = round((display_rect.y() + display_rect.height()) / scale)

        image_width = self.original_pixmap.width()
        image_height = self.original_pixmap.height()
        left = max(0, min(left, image_width - 1))
        top = max(0, min(top, image_height - 1))
        right = max(left + 1, min(right, image_width))
        bottom = max(top + 1, min(bottom, image_height))
        return QtCore.QRect(left, top, right - left, bottom - top)

    def original_rect_to_display(self, original_rect):
        """将原图坐标中的裁切框转换为当前显示坐标。"""
        scale = self.get_display_scale()
        left = round(original_rect.x() * scale)
        top = round(original_rect.y() * scale)
        right = round((original_rect.x() + original_rect.width()) * scale)
        bottom = round((original_rect.y() + original_rect.height()) * scale)
        return QtCore.QRect(left, top, right - left, bottom - top)

    def adjust_image_to_window(self):
        """根据窗口大小等比例缩放图片（保留边距）"""
        if self.original_pixmap and not self.original_pixmap.isNull():
            # 获取窗口客户区大小（去除边框）
            viewport_rect = self.scroll_area.viewport().rect()
            viewport_width = viewport_rect.width()
            viewport_height = viewport_rect.height()

            # 计算缩放比例（留5%边距，避免紧贴窗口）
            width_scale = viewport_width / self.original_pixmap.width() * 0.95
            height_scale = viewport_height / self.original_pixmap.height() * 0.95
            self.current_scale = min(width_scale, height_scale, 1.0)  # 不放大图片
            self.update_displayed_image()

    def resizeEvent(self, event):
        """窗口大小变化时自动适应（如果启用）"""
        if self.auto_adjust_window and self.original_pixmap and not self.original_pixmap.isNull():
            self.adjust_image_to_window()
        super().resizeEvent(event)

    def keyPressEvent(self, event):
        """处理键盘事件：W上一张，S下一张，支持缩放快捷键"""
        if event.key() in [QtCore.Qt.Key.Key_W, QtCore.Qt.Key.Key_S]:
            # 切换图片前保存当前缩放比例
            if 0 <= self.current_index < len(self.image_paths):
                current_path = self.image_paths[self.current_index]
                self.scale_history[current_path] = self.current_scale

        if event.key() == QtCore.Qt.Key.Key_W:
            # 上一张（循环）
            if self.image_paths:
                self.current_index = (self.current_index - 1) % len(self.image_paths)
                self.load_image_by_index(self.current_index)
        elif event.key() == QtCore.Qt.Key.Key_S:
            # 下一张（循环）
            if self.image_paths:
                self.current_index = (self.current_index + 1) % len(self.image_paths)
                self.load_image_by_index(self.current_index)
        # 缩放快捷键
        elif event.key() == QtCore.Qt.Key.Key_Plus and event.modifiers() & QtCore.Qt.KeyboardModifier.ControlModifier:
            self.zoom_in()
        elif event.key() == QtCore.Qt.Key.Key_Minus and event.modifiers() & QtCore.Qt.KeyboardModifier.ControlModifier:
            self.zoom_out()
        elif event.key() == QtCore.Qt.Key.Key_0 and event.modifiers() & QtCore.Qt.KeyboardModifier.ControlModifier:
            self.current_scale = 1.0  # 重置为100%
            self.update_displayed_image()
            self.set_status("缩放: 100%")
        super().keyPressEvent(event)

    def wheelEvent(self, event):
        """鼠标滚轮事件：缩放图片（手动操作后禁用自动适应）"""
        self.handle_wheel_zoom(event)

    def handle_wheel_zoom(self, event):
        """按滚轮方向缩放图片。"""
        if self.original_pixmap and not self.original_pixmap.isNull():
            # 手动缩放后禁用自动适应
            self.auto_adjust_window = False
            self.auto_fit_on_load = False

            # 保存当前缩放比例到历史记录
            if 0 <= self.current_index < len(self.image_paths):
                current_path = self.image_paths[self.current_index]
                self.scale_history[current_path] = self.current_scale

            # 执行缩放
            delta = event.angleDelta().y()
            if delta > 0:
                self.zoom_in()
            else:
                self.zoom_out()
            event.accept()

    def eventFilter(self, watched, event):
        """在图片与视口上处理滚轮缩放和中键平移。"""
        interactive_widgets = (self.image_label, self.scroll_area.viewport())
        if watched in interactive_widgets:
            if event.type() == QtCore.QEvent.Type.Wheel:
                self.handle_wheel_zoom(event)
                return True

            if event.type() == QtCore.QEvent.Type.MouseButtonPress:
                if event.button() == QtCore.Qt.MouseButton.MiddleButton:
                    self.is_panning = True
                    self.pan_last_global_pos = event.globalPosition().toPoint()
                    self.scroll_area.viewport().setCursor(
                        QtCore.Qt.CursorShape.ClosedHandCursor
                    )
                    return True

            if event.type() == QtCore.QEvent.Type.MouseMove and self.is_panning:
                current_global_pos = event.globalPosition().toPoint()
                delta = current_global_pos - self.pan_last_global_pos
                horizontal_bar = self.scroll_area.horizontalScrollBar()
                vertical_bar = self.scroll_area.verticalScrollBar()
                horizontal_bar.setValue(horizontal_bar.value() - delta.x())
                vertical_bar.setValue(vertical_bar.value() - delta.y())
                self.pan_last_global_pos = current_global_pos
                return True

            if event.type() == QtCore.QEvent.Type.MouseButtonRelease:
                if event.button() == QtCore.Qt.MouseButton.MiddleButton and self.is_panning:
                    self.is_panning = False
                    cursor = (
                        QtCore.Qt.CursorShape.CrossCursor
                        if self.crop_mode
                        else QtCore.Qt.CursorShape.ArrowCursor
                    )
                    self.scroll_area.viewport().setCursor(cursor)
                    return True

        return super().eventFilter(watched, event)

    def set_status(self, message):
        """更新状态栏信息"""
        self.statusBar().showMessage(message)

    def show_context_menu(self, position):
        """显示右键菜单"""
        if self.current_index >= 0 and self.current_index < len(self.image_paths):
            self.toggle_crop_action.setText("禁用裁切模式" if self.crop_mode else "启用裁切模式")
            self.context_clear_crops_action.setEnabled(len(self.crop_rects) > 0)
            self.context_save_crops_action.setEnabled(len(self.crop_rects) > 0)
            self.undo_action.setEnabled(self.history_index >= 0)
            self.context_menu.exec(self.mapToGlobal(position))

    def select_current_image(self):
        """选中当前图片（在列表中高亮显示）"""
        if hasattr(self, 'main_ui') and hasattr(self.main_ui, 'image_list'):
            if 0 <= self.current_index < self.main_ui.image_list.count():
                item = self.main_ui.image_list.item(self.current_index)
                self.main_ui.image_list.setCurrentItem(item)

                # 如果裁切窗口打开且自动刷新启用，则更新显示
                if hasattr(self.main_ui, 'new_window') and self.main_ui.new_window and self.main_ui.new_window.isVisible():
                    if self.main_ui.new_window.auto_refresh_enabled:
                        self.main_ui.new_window.update_display()

    def copy_image_path(self):
        """复制当前图片路径到剪贴板"""
        if self.current_index >= 0 and self.current_index < len(self.image_paths):
            image_path = self.image_paths[self.current_index]
            clipboard = QApplication.clipboard()
            clipboard.setText(image_path)
            self.set_status(f"已复制图片路径: {image_path}")

    def open_in_explorer(self):
        """在资源管理器中打开图片所在文件夹"""
        if self.current_index >= 0 and self.current_index < len(self.image_paths):
            image_path = self.image_paths[self.current_index]
            image_dir = os.path.dirname(image_path)

            # 根据不同操作系统执行不同命令
            if sys.platform.startswith('win'):
                os.startfile(image_dir)  # Windows系统
            elif sys.platform.startswith('darwin'):
                subprocess.run(['open', image_dir])  # macOS系统
            else:
                subprocess.run(['xdg-open', image_dir])  # Linux系统

    def toggle_crop_mode(self):
        """切换裁切模式"""
        self.crop_mode = not self.crop_mode
        self.crop_mode_action.setText("禁用裁切模式" if self.crop_mode else "启用裁切模式")
        self.crop_mode_action.setChecked(self.crop_mode)

        if self.crop_mode:
            self.set_status("裁切模式已启用 - 拖动鼠标选择区域")
            self.image_label.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.CrossCursor))
        else:
            self.set_status("裁切模式已禁用")
            self.image_label.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.ArrowCursor))

        self.update_crop_buttons_status()
        self.image_label.update()

    def clear_crop_rects(self):
        """清除所有裁切框"""
        if self.crop_rects:
            self.add_history_action("clear", self.crop_rects.copy())
            self.crop_rects = []
            self.current_crop_rect = None
            self.image_label.update()
            self.update_crop_buttons_status()
            self.set_status("已清除所有裁切框")

    def add_crop_rect(self, rect):
        """添加一个以原图坐标保存的裁切框并记录操作。"""
        self.add_history_action("add", rect)
        self.crop_rects.append(rect)
        self.image_label.update()
        self.update_crop_buttons_status()

    def add_history_action(self, action_type, data):
        """添加操作到历史记录"""
        if self.history_index < len(self.crop_history) - 1:
            self.crop_history = self.crop_history[:self.history_index + 1]
        self.crop_history.append((action_type, data))
        self.history_index += 1
        self.update_history_buttons()

    def undo_last_crop(self):
        """撤销上一步操作"""
        if self.history_index >= 0:
            action = self.crop_history[self.history_index]
            action_type, data = action

            if action_type == "add" and self.crop_rects:
                self.crop_rects.pop()
            elif action_type == "clear":
                self.crop_rects = data.copy()
            elif action_type == "delete":
                index, rect = data
                self.crop_rects.insert(index, rect)

            self.history_index -= 1
            self.image_label.update()
            self.update_crop_buttons_status()
            self.update_history_buttons()
            self.set_status("已撤销上一步操作")

    def update_crop_buttons_status(self):
        """更新裁切相关按钮状态"""
        has_crops = len(self.crop_rects) > 0
        self.clear_crops_action.setEnabled(has_crops)
        self.save_crops_action.setEnabled(has_crops)
        self.context_clear_crops_action.setEnabled(has_crops)
        self.context_save_crops_action.setEnabled(has_crops)

    def update_history_buttons(self):
        """更新历史操作按钮状态"""
        self.undo_action.setEnabled(self.history_index >= 0)

    def save_all_crops(self):
        """保存所有裁切区域"""
        if not self.original_pixmap or len(self.crop_rects) == 0:
            return

        output_dir = self.main_ui.output_directory_line_edit.text()
        if not output_dir:
            QMessageBox.warning(self, "警告", "请先设置输出目录")
            return

        # 确保输出目录存在
        if not os.path.exists(output_dir):
            try:
                os.makedirs(output_dir)
            except Exception as e:
                QMessageBox.warning(self, "错误", f"无法创建输出目录: {str(e)}")
                return

        # 获取当前图片名称和用户自定义命名
        current_image_name = os.path.basename(self.image_paths[self.current_index])
        base_name, ext = os.path.splitext(current_image_name)
        custom_name, ok = QInputDialog.getText(
            self, "自定义命名", "请输入裁切图片的前缀 (留空则使用原图名称):", text=base_name
        )
        if ok:
            if custom_name.strip():
                base_name = custom_name.strip()

            # 保存每个裁切区域
            saved_count = 0
            for i, rect in enumerate(self.crop_rects):
                try:
                    # 裁切框已经使用原图坐标保存，不受当前显示缩放影响。
                    cropped_pixmap = self.original_pixmap.copy(rect)
                    crop_name = f"{base_name}_crop_{i + 1}{ext}"
                    crop_path = os.path.join(output_dir, crop_name)

                    if cropped_pixmap.save(crop_path):
                        saved_count += 1
                    else:
                        QMessageBox.warning(self, "保存失败", f"无法保存裁切图片: {crop_path}")
                except Exception as e:
                    QMessageBox.warning(self, "保存失败", f"保存过程中发生错误: {str(e)}")

            if saved_count > 0:
                self.set_status(f"成功保存 {saved_count} 个裁切图片到 {output_dir}")
                if hasattr(self.main_ui, 'new_window') and self.main_ui.new_window and self.main_ui.new_window.isVisible():
                    if self.main_ui.new_window.auto_refresh_enabled:
                        self.main_ui.new_window.update_display()
            else:
                self.set_status("没有保存任何裁切图片")

    def show_crop_settings(self):
        """显示裁切设置对话框"""
        dialog = QDialog(self)
        dialog.setWindowTitle("裁切设置")
        dialog.setMinimumWidth(300)

        layout = QVBoxLayout(dialog)

        # 颜色选择
        color_group = QGroupBox("裁切框颜色")
        color_layout = QHBoxLayout(color_group)
        color_label = QLabel("当前颜色:")
        color_preview = QLabel()
        color_preview.setFixedSize(20, 20)
        color_preview.setStyleSheet(f"background-color: {self.crop_color.name()};")
        color_button = QPushButton("选择颜色...")
        color_button.clicked.connect(lambda: self.select_crop_color(color_preview))
        color_layout.addWidget(color_label)
        color_layout.addWidget(color_preview)
        color_layout.addWidget(color_button)
        layout.addWidget(color_group)

        # 线条宽度选择
        width_group = QGroupBox("裁切框线条宽度")
        width_layout = QHBoxLayout(width_group)
        width_label = QLabel("宽度:")
        width_spinbox = QSpinBox()
        width_spinbox.setRange(1, 10)
        width_spinbox.setValue(self.crop_line_width)
        width_spinbox.valueChanged.connect(self.set_crop_line_width)
        width_layout.addWidget(width_label)
        width_layout.addWidget(width_spinbox)
        layout.addWidget(width_group)

        # 确认按钮
        ok_button = QPushButton("确定")
        ok_button.clicked.connect(dialog.accept)
        layout.addWidget(ok_button)

        dialog.exec()

    def select_crop_color(self, preview_label):
        """选择裁切框颜色"""
        color = QColorDialog.getColor(self.crop_color, self, "选择裁切框颜色")
        if color.isValid():
            self.crop_color = color
            preview_label.setStyleSheet(f"background-color: {color.name()};")
            self.image_label.update()

    def set_crop_line_width(self, width):
        """设置裁切框线条宽度"""
        self.crop_line_width = width
        self.image_label.update()

    def zoom_in(self):
        """放大图片（手动操作后禁用自动适应）"""
        if self.original_pixmap and not self.original_pixmap.isNull():
            self.auto_adjust_window = False  # 手动缩放后禁用自动适应
            self.current_scale *= 1.2
            self.update_displayed_image()
            self.set_status(f"缩放: {int(self.current_scale * 100)}%")
            # 保存当前缩放比例
            if 0 <= self.current_index < len(self.image_paths):
                current_path = self.image_paths[self.current_index]
                self.scale_history[current_path] = self.current_scale

    def zoom_out(self):
        """缩小图片（手动操作后禁用自动适应）"""
        if self.original_pixmap and not self.original_pixmap.isNull():
            self.auto_adjust_window = False  # 手动缩放后禁用自动适应
            self.current_scale *= 0.8
            self.current_scale = max(0.1, self.current_scale)  # 限制最小缩放
            self.update_displayed_image()
            self.set_status(f"缩放: {int(self.current_scale * 100)}%")
            # 保存当前缩放比例
            if 0 <= self.current_index < len(self.image_paths):
                current_path = self.image_paths[self.current_index]
                self.scale_history[current_path] = self.current_scale


# 自定义图片标签，用于处理鼠标事件和显示裁切框
class CustomImageLabel(QLabel):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.setMouseTracking(True)

    def mousePressEvent(self, event):
        """鼠标按下事件"""
        if self.parent.crop_mode and event.button() == QtCore.Qt.MouseButton.LeftButton:
            self.parent.drawing = True
            self.parent.start_point = event.pos()
            self.parent.end_point = event.pos()
            self.parent.current_crop_rect = None

    def mouseMoveEvent(self, event):
        """鼠标移动事件"""
        if self.parent.crop_mode and self.parent.drawing:
            self.parent.end_point = event.pos()
            self.update()

    def mouseReleaseEvent(self, event):
        """鼠标释放事件"""
        if self.parent.crop_mode and event.button() == QtCore.Qt.MouseButton.LeftButton:
            self.parent.drawing = False
            self.parent.end_point = event.pos()

            # 创建裁切矩形
            x = min(self.parent.start_point.x(), self.parent.end_point.x())
            y = min(self.parent.start_point.y(), self.parent.end_point.y())
            width = abs(self.parent.start_point.x() - self.parent.end_point.x())
            height = abs(self.parent.start_point.y() - self.parent.end_point.y())

            if width > 0 and height > 0:
                display_rect = QtCore.QRect(x, y, width, height)
                original_rect = self.parent.display_rect_to_original(display_rect)
                self.parent.add_crop_rect(original_rect)
                self.parent.set_status(
                    f"添加了一个裁切区域: {original_rect.width()}x{original_rect.height()}"
                )
            else:
                self.parent.set_status("裁切区域太小，已忽略")

            self.parent.current_crop_rect = None
            self.update()

    def paintEvent(self, event):
        """绘制事件"""
        super().paintEvent(event)

        if not self.pixmap() or (not self.parent.crop_mode and not self.parent.crop_rects):
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 绘制所有已保存的裁切框
        for i, rect in enumerate(self.parent.crop_rects):
            display_rect = self.parent.original_rect_to_display(rect)
            pen = QPen(self.parent.crop_color, self.parent.crop_line_width)
            painter.setPen(pen)
            painter.drawRect(display_rect)

            # 绘制裁切框编号
            painter.setPen(QPen(self.parent.crop_color, 1))
            painter.drawText(display_rect.x() + 5, display_rect.y() + 20, f"裁切 {i + 1}")

        # 绘制当前正在绘制的裁切框
        if self.parent.drawing and self.parent.start_point != self.parent.end_point:
            x = min(self.parent.start_point.x(), self.parent.end_point.x())
            y = min(self.parent.start_point.y(), self.parent.end_point.y())
            width = abs(self.parent.start_point.x() - self.parent.end_point.x())
            height = abs(self.parent.start_point.y() - self.parent.end_point.y())

            current_rect = QtCore.QRect(x, y, width, height)
            pen = QPen(self.parent.crop_color, self.parent.crop_line_width)
            painter.setPen(pen)
            painter.drawRect(current_rect)

            # 显示当前尺寸
            painter.setPen(QPen(self.parent.crop_color, 1))
            painter.drawText(current_rect.x() + 5, current_rect.y() + 20, f"{width}x{height}")


# 改进的裁切窗口类（支持图片删除功能和右键查看图片路径）
class NewWindow(QDialog):
    def __init__(self, parent=None, main_ui=None):
        super().__init__(parent)
        self.setWindowTitle("裁切后")
        self.resize(800, 600)

        self.main_ui = main_ui
        self.output_dir = main_ui.output_directory_line_edit.text()
        self.images_data = {}  # 存储图片路径和对应的标签

        # 创建主布局
        layout = QVBoxLayout(self)

        # 创建按钮布局
        button_layout = QHBoxLayout()

        # 添加刷新按钮
        refresh_button = QPushButton("刷新", self)
        refresh_button.clicked.connect(self.refresh_display)
        button_layout.addWidget(refresh_button)

        # 添加自动刷新复选框
        self.auto_refresh_checkbox = QCheckBox("自动刷新", self)
        self.auto_refresh_checkbox.setChecked(True)  # 默认开启自动刷新
        self.auto_refresh_checkbox.stateChanged.connect(self.toggle_auto_refresh)
        button_layout.addWidget(self.auto_refresh_checkbox)

        # 删除选中图片按钮
        self.delete_button = QPushButton("删除选中图片", self)
        self.delete_button.clicked.connect(self.delete_selected_images)
        self.delete_button.setEnabled(False)  # 初始禁用
        button_layout.addWidget(self.delete_button)

        # 关闭按钮
        close_button = QPushButton("关闭", self)
        close_button.clicked.connect(self.close)
        button_layout.addWidget(close_button)

        layout.addLayout(button_layout)

        # 创建滚动区域
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)

        # 创建图片显示区域
        self.image_widget = QWidget()
        self.image_layout = QGridLayout(self.image_widget)
        self.image_layout.setSpacing(10)

        self.scroll_area.setWidget(self.image_widget)
        layout.addWidget(self.scroll_area)

        # 状态栏
        self.status_label = QLabel("就绪")
        layout.addWidget(self.status_label)

        # 初始化显示
        self.auto_refresh_enabled = True
        self.update_display()

        # 右键菜单支持
        self.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)

        # 创建右键菜单
        self.context_menu = QMenu(self)

        # 右键菜单项
        self.copy_path_action = QAction("复制图片路径", self)
        self.copy_path_action.triggered.connect(self.copy_selected_image_path)
        self.context_menu.addAction(self.copy_path_action)

        self.open_in_explorer_action = QAction("在资源管理器中打开", self)
        self.open_in_explorer_action.triggered.connect(self.open_image_in_explorer)
        self.context_menu.addAction(self.open_in_explorer_action)

        # 分隔线
        self.context_menu.addSeparator()

        self.delete_action = QAction("删除图片", self)
        self.delete_action.triggered.connect(self.delete_selected_images)
        self.context_menu.addAction(self.delete_action)

    def toggle_auto_refresh(self, state):
        """切换自动刷新状态"""
        self.auto_refresh_enabled = state == QtCore.Qt.CheckState.Checked
        status = "开启" if self.auto_refresh_enabled else "关闭"
        self.status_label.setText(f"自动刷新: {status}")

    def refresh_display(self):
        """手动刷新显示"""
        self.output_dir = self.main_ui.output_directory_line_edit.text()
        self.update_display()
        self.status_label.setText("刷新完成")

    def update_display(self):
        """更新显示内容"""
        # 清空现有内容和数据
        self.images_data = {}
        for i in reversed(range(self.image_layout.count())):
            widget = self.image_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)

        # 获取当前选中的图片
        current_item = self.main_ui.image_list.currentItem()
        if not current_item:
            self.status_label.setText("未选择图片")
            self.delete_button.setEnabled(False)
            return

        # 获取图片前缀
        file_name = current_item.text()
        prefix = os.path.splitext(file_name)[0]

        # 更新状态栏
        self.status_label.setText(f"正在加载 {prefix} 的裁切结果...")

        # 筛选输出目录中的图片
        if os.path.exists(self.output_dir):
            try:
                output_files = os.listdir(self.output_dir)
                matching_files = []

                for file in output_files:
                    file_prefix = os.path.splitext(file)[0]
                    if prefix in file_prefix:
                        matching_files.append(file)

                if not matching_files:
                    self.status_label.setText(f"未找到 {prefix} 的裁切结果")
                    self.delete_button.setEnabled(False)
                    return

                # 显示匹配的图片
                row = 0
                col = 0
                for file in matching_files:
                    file_path = os.path.join(self.output_dir, file)
                    pixmap = QtGui.QPixmap(file_path)
                    if not pixmap.isNull():
                        # 创建图片容器
                        image_container = QWidget()
                        container_layout = QVBoxLayout(image_container)
                        container_layout.setContentsMargins(0, 0, 0, 0)

                        # 缩放图片为缩略图
                        thumbnail = pixmap.scaled(200, 200, QtCore.Qt.AspectRatioMode.KeepAspectRatio)
                        label = QLabel()
                        label.setPixmap(thumbnail)
                        label.setToolTip(file)  # 鼠标悬停显示完整文件名
                        label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
                        self.set_image_selected(label, False)

                        # 为标签添加点击事件
                        label.mousePressEvent = lambda event, l=label: self.on_image_clicked(l, event)

                        # 添加文件名标签
                        name_label = QLabel(file)
                        name_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
                        name_label.setWordWrap(True)

                        container_layout.addWidget(label)
                        container_layout.addWidget(name_label)

                        # 将容器添加到网格布局
                        self.image_layout.addWidget(image_container, row, col)

                        # 保存图片路径和标签的映射
                        self.images_data[file_path] = label

                        col += 1
                        if col >= 4:
                            col = 0
                            row += 1

                self.status_label.setText(f"已加载 {len(matching_files)} 张图片")
                self.update_delete_button_state()
            except Exception as e:
                self.status_label.setText(f"加载图片时出错: {str(e)}")
                self.delete_button.setEnabled(False)
        else:
            self.status_label.setText(f"输出目录不存在: {self.output_dir}")
            self.delete_button.setEnabled(False)

    def on_image_clicked(self, label, event):
        """处理图片点击事件（选择/取消选择）"""
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            self.set_image_selected(label, not self.is_image_selected(label))
            self.update_delete_button_state()

    @staticmethod
    def is_image_selected(label):
        """返回缩略图是否处于选中状态。"""
        return bool(label.property("image_selected"))

    @staticmethod
    def set_image_selected(label, selected):
        """设置缩略图选中态，使用描边避免被图片内容遮挡。"""
        label.setProperty("image_selected", selected)
        if selected:
            label.setStyleSheet(
                "QLabel { border: 4px solid #0078D7; background-color: #D9EEFF; }"
            )
        else:
            label.setStyleSheet(
                "QLabel { border: 4px solid transparent; background-color: transparent; }"
            )

    def update_delete_button_state(self):
        """更新删除按钮状态（是否有选中的图片）"""
        selected_count = self.get_selected_images_count()
        self.delete_button.setEnabled(selected_count > 0)
        self.delete_button.setText(f"删除选中图片 ({selected_count})")

    def get_selected_images_count(self):
        """获取选中的图片数量"""
        count = 0
        for path, label in self.images_data.items():
            if self.is_image_selected(label):
                count += 1
        return count

    def get_selected_images(self):
        """获取选中的图片路径列表"""
        selected = []
        for path, label in self.images_data.items():
            if self.is_image_selected(label):
                selected.append(path)
        return selected

    def delete_selected_images(self):
        """删除选中的图片"""
        selected_images = self.get_selected_images()
        if not selected_images:
            return

        # 确认对话框
        reply = QMessageBox.question(
            self,
            "确认删除",
            f"确定要删除选中的 {len(selected_images)} 张图片吗？此操作不可撤销。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            deleted_count = 0
            for image_path in selected_images:
                try:
                    os.remove(image_path)
                    deleted_count += 1
                except Exception as e:
                    self.status_label.setText(f"删除失败: {str(e)}")
                    return

            self.status_label.setText(f"成功删除 {deleted_count} 张图片")
            self.refresh_display()  # 刷新显示

    def show_context_menu(self, position):
        """显示右键菜单"""
        # 检查点击位置是否在图片上
        child = self.childAt(position)
        if isinstance(child, QLabel) and child in self.images_data.values():
            # 右键操作始终针对当前图片，避免保留多选导致“在资源管理器中打开”失效。
            for label in self.images_data.values():
                self.set_image_selected(label, label is child)
            self.update_delete_button_state()

            self.context_menu.exec(self.mapToGlobal(position))

    def copy_selected_image_path(self):
        """复制选中图片的路径到剪贴板"""
        selected_images = self.get_selected_images()
        if len(selected_images) == 1:
            clipboard = QApplication.clipboard()
            clipboard.setText(selected_images[0])
            self.status_label.setText(f"已复制图片路径: {os.path.basename(selected_images[0])}")
        elif len(selected_images) > 1:
            self.status_label.setText("请仅选择一张图片以复制路径")
        else:
            self.status_label.setText("未选择图片")

    def open_image_in_explorer(self):
        """在资源管理器中定位并选中当前图片。"""
        selected_images = self.get_selected_images()
        if len(selected_images) == 1:
            image_path = selected_images[0]

            try:
                if sys.platform.startswith('win'):
                    subprocess.Popen([
                        'explorer.exe',
                        '/select,',
                        os.path.normpath(image_path),
                    ])
                elif sys.platform.startswith('darwin'):
                    subprocess.run(['open', '-R', image_path], check=True)
                else:
                    subprocess.run(['xdg-open', os.path.dirname(image_path)], check=True)

                self.status_label.setText(f"已在资源管理器中定位: {os.path.basename(image_path)}")
            except Exception as e:
                self.status_label.setText(f"无法在资源管理器中打开: {str(e)}")
        elif len(selected_images) > 1:
            self.status_label.setText("请仅选择一张图片以在资源管理器中打开")
        else:
            self.status_label.setText("未选择图片")


# 支持拖放的图片列表控件
class DragDropImageList(QListWidget):
    def __init__(self, parent_ui):
        super().__init__()
        self.parent_ui = parent_ui
        self.setAcceptDrops(True)
        self.setAlternatingRowColors(True)
        self.setToolTip("可拖拽图片文件到此处")

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if url.isLocalFile():
                    file_path = url.toLocalFile()
                    if os.path.isfile(file_path):
                        ext = os.path.splitext(file_path)[1].lower()
                        if ext in supported_types:
                            event.acceptProposedAction()
                            return
        event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            event.setDropAction(QtCore.Qt.DropAction.CopyAction)
            event.accept()

            added_count = 0
            for url in event.mimeData().urls():
                if url.isLocalFile():
                    file_path = url.toLocalFile()
                    if os.path.isfile(file_path):
                        file_name = os.path.basename(file_path)
                        file_dir = os.path.dirname(file_path)

                        # 检查重复
                        is_duplicate = False
                        for i in range(self.count()):
                            stored_path = self.item(i).data(QtCore.Qt.ItemDataRole.UserRole)
                            if stored_path and stored_path == file_path:
                                is_duplicate = True
                                break

                        if not is_duplicate:
                            item = QListWidgetItem(file_name)
                            item.setData(QtCore.Qt.ItemDataRole.UserRole, file_path)
                            self.addItem(item)

                            if not self.parent_ui.current_directory:
                                self.parent_ui.current_directory = file_dir

                            added_count += 1

            if added_count > 0:
                self.parent_ui.set_status(f"成功添加 {added_count} 张图片")
        else:
            event.ignore()


class MainWindowUI(Ui_MainWindow):
    def __init__(self, window: QMainWindow) -> None:

        super().__init__()

        self.window = window
        self.setupUi(window)

        # 初始化图像查看窗口
        self.image_viewer = ImageViewerWindow(self.window)
        self.image_viewer.main_ui = self  # 保存对main_ui的引用

        # 初始化变量
        self.current_directory = ""
        self.image_files = []

        # 创建主分割器布局
        self.create_main_splitter_layout()

        # 按钮事件绑定
        self.input_directory_browse_button.clicked.connect(self.open_input_directory_dialog)
        self.output_directory_browse_button.clicked.connect(self.open_output_directory_dialog)
        self.start_button.clicked.connect(self.start_extracting)
        self.cancel_button.clicked.connect(self.cancel_extraction)

        self.window.setWindowIcon(QtGui.QIcon(resource_path("icon.ico")))

        # 新窗口相关
        self.new_window = None
        self.open_new_window_button = QPushButton("裁切图片查看", self.centralwidget)
        self.open_new_window_button.clicked.connect(self.show_new_window)
        self.verticalLayout_2.addWidget(self.open_new_window_button)

        # RunningHub处理按钮
    #    self.runninghub_btn = QPushButton("RunningHub处理", self.centralwidget)
 #      self.runninghub_btn.setStyleSheet("""
   #         background-color-color: #4CAF50; 
   #         color: white; 
   #         padding: 5px;
  ##          border-radius: 3px;
   #     """)
   #     self.runninghub_btn.clicked.connect(self.open_runninghub_window)
   #     self.verticalLayout_2.addWidget(self.runninghub_btn)
#
   #     # 连接图像查看器的信号
   #     self.image_viewer.image_changed.connect(self.on_image_viewer_changed)

 #   def open_runninghub_window(self):
  #      """打开RunningHub独立窗口，并同步当前图片列表"""
  #      if self.image_list.count() == 0:
  #          QMessageBox.warning(self.window, "提示", "请先添加图片到列表")
  #          return
#
   #     # 创建RunningHub窗口实例
   #     self.runninghub_window = RunningHubStandaloneWindow()
#
   #     # 同步主窗口的图片到RunningHub窗口
    #    image_paths = self.get_all_image_paths()
    #    self.runninghub_window.image_paths = image_paths
        # 在新窗口列表中显示文件名
   #     for path in image_paths:
    #        self.runninghub_window.image_list.addItem(os.path.basename(path))
#
    #    # 显示窗口
    #    self.runninghub_window.show()
    #    self.runninghub_window.raise_()  # 窗口置顶

    def create_main_splitter_layout(self):
        self.main_splitter = QSplitter(QtCore.Qt.Orientation.Horizontal)

        self.original_central_widget = self.centralwidget
        self.original_layout = self.centralwidget.layout()

        self.left_panel = QWidget()
        self.left_layout = QVBoxLayout(self.left_panel)
        self.left_layout.setContentsMargins(5, 5, 5, 5)
        self.left_layout.setSpacing(5)

        self.create_image_list_section()

        self.right_panel = QWidget()
        self.right_layout = QVBoxLayout(self.right_panel)
        self.right_layout.setContentsMargins(0, 0, 0, 0)

        self.original_central_widget.setParent(self.right_panel)
        self.right_layout.addWidget(self.original_central_widget)

        self.main_splitter.addWidget(self.left_panel)
        self.main_splitter.addWidget(self.right_panel)
        self.main_splitter.setSizes([300, 700])

        self.window.setCentralWidget(self.main_splitter)

    def create_image_list_section(self):
        self.list_label = QLabel("图片文件列表（支持拖拽添加）")
        self.list_label.setStyleSheet("font-weight: bold;")
        self.left_layout.addWidget(self.list_label)

        self.image_list = DragDropImageList(self)
        self.image_list.itemClicked.connect(self.on_image_selected)
        self.image_list.setMinimumWidth(200)
        self.left_layout.addWidget(self.image_list)

        self.button_layout = QHBoxLayout()

        self.view_button = QPushButton("查看选中图片")
        self.view_button.clicked.connect(self.view_image_in_window)
        self.button_layout.addWidget(self.view_button)

        self.clear_list_button = QPushButton("清空列表")
        self.clear_list_button.clicked.connect(self.clear_image_list)
        self.button_layout.addWidget(self.clear_list_button)

        self.left_layout.addLayout(self.button_layout)

    def open_input_directory_dialog(self):
        directory = str(QFileDialog.getExistingDirectory(self.window, "Select Input Directory"))
        if directory:
            self.current_directory = directory
            self.input_directory_line_edit.setText(directory)
            self.load_image_files()

    def load_image_files(self):
        if not self.current_directory:
            return

        try:
            file_names = get_file_names(self.current_directory)
            self.image_files = [
                f for f in file_names
                if os.path.splitext(f)[1].lower() in supported_types
            ]

            self.image_list.clear()
            for file in self.image_files:
                item = QListWidgetItem(file)
                full_path = os.path.join(self.current_directory, file)
                item.setData(QtCore.Qt.ItemDataRole.UserRole, full_path)
                self.image_list.addItem(item)

            count = len(self.image_files)
            self.set_status(f"找到 {count} 张图片，已添加到列表")
        except Exception as e:
            self.set_status(f"加载图片时出错: {str(e)}")

    def get_all_image_paths(self):
        """获取列表中所有图片的完整路径"""
        paths = []
        for i in range(self.image_list.count()):
            item = self.image_list.item(i)
            path = item.data(QtCore.Qt.ItemDataRole.UserRole)
            if path:
                paths.append(path)
        return paths

    def on_image_selected(self, item):
        if not item:
            return

        image_path = item.data(QtCore.Qt.ItemDataRole.UserRole)
        if not image_path:
            if not self.current_directory:
                self.set_status("没有可用的图片路径")
                return
            image_path = os.path.join(self.current_directory, item.text())

        pixmap = QtGui.QPixmap(image_path)
        if not pixmap.isNull():
            # 获取当前选中项的索引，用于图片切换
            current_index = self.image_list.row(item)
            all_paths = self.get_all_image_paths()
            self.image_viewer.set_image_list(all_paths, current_index)
            self.set_status(f"选中图片: {item.text()}")
        else:
            self.set_status(f"无法加载图片: {image_path}")

    def view_image_in_window(self):
        """无选中项时自动显示列表第一张图片"""
        if self.image_list.count() == 0:
            self.set_status("列表中没有图片可查看")
            return

        # 获取当前选中项，若无则自动选择第一项
        current_item = self.image_list.currentItem()
        if not current_item:
            current_item = self.image_list.item(0)
            self.image_list.setCurrentItem(current_item)

        # 加载选中的图片
        image_path = current_item.data(QtCore.Qt.ItemDataRole.UserRole)
        if not image_path:
            if not self.current_directory:
                self.set_status("没有可用的图片路径")
                return
            image_path = os.path.join(self.current_directory, current_item.text())

        pixmap = QtGui.QPixmap(image_path)
        if not pixmap.isNull():
            current_index = self.image_list.row(current_item)
            all_paths = self.get_all_image_paths()
            self.image_viewer.set_image_list(all_paths, current_index)
            self.image_viewer.show()  # 显示窗口时自动适应图片
        else:
            self.set_status(f"无法加载图片: {image_path}")

    def clear_image_list(self):
        """清空图片列表并关闭裁切窗口和图像查看器"""
        self.image_list.clear()
        self.image_files = []

        # 关闭裁切窗口
        if self.new_window and self.new_window.isVisible():
            self.new_window.close()
            self.new_window = None

        # 关闭图像查看器
        if self.image_viewer.isVisible():
            self.image_viewer.close()

        self.set_status("图片列表已清空，裁切窗口和图像查看器已关闭")

    def show_new_window(self):
        """显示裁切图片查看窗口，确保只打开一个实例"""
        output_dir = self.output_directory_line_edit.text()
        if output_dir and self.image_list.count() > 0:
            # 获取当前选中的图片
            current_item = self.image_list.currentItem()
            if current_item:
                # 如果窗口已存在但被隐藏，则显示它
                if self.new_window and not self.new_window.isVisible():
                    self.new_window = None

                # 如果窗口不存在或已关闭，则创建新窗口
                if not self.new_window:
                    self.new_window = NewWindow(self.window, self)
                    self.new_window.finished.connect(self.on_new_window_closed)

                # 显示窗口并更新内容
                self.new_window.show()
                self.new_window.raise_()
                self.new_window.activateWindow()

                # 更新裁切窗口显示
                self.new_window.update_display()
            else:
                self.set_status("请先选择一张图片")
        else:
            self.set_status("请先设置输出目录并选择图片")

    def on_new_window_closed(self):
        """当裁切窗口关闭时调用，重置窗口引用"""
        self.new_window = None

    def on_image_viewer_changed(self, index):
        """处理图像查看器的图片变更事件"""
        if self.new_window and self.new_window.isVisible():
            if 0 <= index < self.image_list.count():
                item = self.image_list.item(index)
                self.image_list.setCurrentItem(item)
                if self.new_window.auto_refresh_enabled:
                    self.new_window.update_display()

    def open_output_directory_dialog(self):
        directory = str(QFileDialog.getExistingDirectory(self.window, "Select Output Directory"))
        self.output_directory_line_edit.setText(directory)

    def update_progress(self, finished: int, total: int):
        self.set_status(f"Processing {finished}/{total}")
        self.progress_bar.setValue(int((finished / total) * 100))

    def set_status(self, message: str):
        self.window.statusBar().showMessage(message)

    def start_extracting(self):
        input_dir = self.input_directory_line_edit.text().strip()
        output_dir = self.output_directory_line_edit.text().strip()
        image_paths = self.get_all_image_paths()

        if not image_paths:
            QMessageBox.warning(self.window, "提示", "请先选择输入目录或拖入至少一张图片")
            return

        if not output_dir:
            QMessageBox.warning(self.window, "提示", "请先选择输出目录")
            return

        try:
            os.makedirs(output_dir, exist_ok=True)
        except OSError as error:
            QMessageBox.warning(self.window, "错误", f"无法创建输出目录：{error}")
            return

        self.input_directory_browse_button.setEnabled(False)
        self.output_directory_browse_button.setEnabled(False)
        self.start_button.setEnabled(False)
        self.cancel_button.setEnabled(True)

        self.extraction_thread = ExtractionThread(
            input_dir,
            output_dir,
            image_paths=image_paths,
            output_to_folders=self.output_separate_folders_check_box.isChecked(),
            merge_mode=self.merge_mode_combo_box.currentIndex()
        )

        self.extraction_thread.progress_update.connect(self.update_progress)
        self.extraction_thread.process_finished.connect(self.extracting_finished)
        self.extraction_thread.start()

    def cancel_extraction(self):
        if hasattr(self, "extraction_thread"):
            self.extraction_thread.requestInterruption()
            self.extraction_thread.wait()

        self.set_status("Cancelled")
        self.input_directory_browse_button.setEnabled(True)
        self.output_directory_browse_button.setEnabled(True)
        self.start_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        self.progress_bar.setValue(0)

    def extracting_finished(self):
        self.input_directory_browse_button.setEnabled(True)
        self.output_directory_browse_button.setEnabled(True)
        self.start_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        self.progress_bar.setValue(100)
        self.set_status("Finished process")
        self.extraction_thread = None


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.ui = MainWindowUI(self)
        self.setWindowTitle("Image Cutter")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
