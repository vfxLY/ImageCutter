# -*- coding: utf-8 -*-
from PyQt6 import QtGui, QtCore
from PyQt6.QtWidgets import QLabel, QScrollArea, QVBoxLayout, QWidget

class ImageViewer(QWidget):
    """图像显示组件，包含缩放、平移和裁切框绘制功能"""
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # 初始化布局
        self.layout = QVBoxLayout(self)
        self.setLayout(self.layout)
        
        # 创建滚动区域
        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll_area.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.layout.addWidget(self.scroll_area)
        
        # 图片显示标签
        self.image_display = QLabel()
        self.image_display.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.scroll_area.setWidget(self.image_display)
        
        # 状态变量
        self.current_pixmap = None  # 保存当前加载的原图
        self.current_image_name = ""  # 保存当前图片名称
        self.crop_regions = []  # 存储所有裁切区域
        self.history = []  # 操作历史记录
        self.moving_crop_index = -1  # 当前正在移动的选框索引
        self.move_offset = QtCore.QPoint()  # 鼠标与选框左上角的偏移量
        
        # 绘图相关变量
        self.drawing = False
        self.start_point = QtCore.QPoint()
        self.end_point = QtCore.QPoint()
        self.current_line_width = 7  # 线框粗细
        
        # 绑定事件
        self.image_display.mousePressEvent = self.mouse_press_event
        self.image_display.mouseMoveEvent = self.mouse_move_event
        self.image_display.mouseReleaseEvent = self.mouse_release_event
        self.scroll_area.resizeEvent = self.on_scroll_area_resize

    def set_image(self, image_path=None, pixmap=None):
        """设置显示的图像"""
        if image_path:
            self.current_pixmap = QtGui.QPixmap(image_path)
        elif pixmap:
            self.current_pixmap = pixmap
            
        self.crop_regions = []  # 清除裁切区域
        self.history = []  # 清空历史记录
        self.update_image_display()

    def update_image_display(self):
        """更新图像显示，包括所有裁切区域"""
        if not self.current_pixmap or self.current_pixmap.isNull():
            return
            
        # 获取显示区域大小
        viewport = self.scroll_area.viewport()
        viewport_width = viewport.width()
        viewport_height = viewport.height()
        
        # 计算缩放比例
        original_width = self.current_pixmap.width()
        original_height = self.current_pixmap.height()
        scale_factor = min(viewport_width / original_width, viewport_height / original_height)
        scaled_width = int(original_width * scale_factor)
        scaled_height = int(original_height * scale_factor)
        
        # 缩放图像
        scaled_pixmap = self.current_pixmap.scaled(
            scaled_width, scaled_height, 
            QtCore.Qt.AspectRatioMode.KeepAspectRatio, 
            QtCore.Qt.TransformationMode.SmoothTransformation
        )
        
        # 绘制裁切区域
        painter = QtGui.QPainter(scaled_pixmap)
        scale_x = scaled_width / original_width
        scale_y = scaled_height / original_height
        
        # 绘制已有的裁切区域
        for i, rect in enumerate(self.crop_regions):
            scaled_rect = QtCore.QRect(
                int(rect.x() * scale_x),
                int(rect.y() * scale_y),
                int(rect.width() * scale_x),
                int(rect.height() * scale_y)
            )
            
            color = self._get_crop_color(i)
            pen = QtGui.QPen(color, self.current_line_width, QtCore.Qt.PenStyle.SolidLine)
            
            if i == self.moving_crop_index:
                pen.setWidth(self.current_line_width + 1)
                
            painter.setPen(pen)
            painter.drawRect(scaled_rect)
            
            # 添加序号标签
            font = painter.font()
            font.setBold(True)
            font.setPointSize(10)
            painter.setFont(font)
            painter.setPen(QtGui.QPen(QtCore.Qt.GlobalColor.red, 2))
            painter.drawText(scaled_rect.topLeft() + QtCore.QPoint(5, 15), f"#{i+1}")
        
        # 绘制正在绘制的裁切框
        if self.drawing and self.start_point != self.end_point:
            scaled_start = QtCore.QPoint(
                int(self.start_point.x() * scale_x),
                int(self.start_point.y() * scale_y)
            )
            scaled_end = QtCore.QPoint(
                int(self.end_point.x() * scale_x),
                int(self.end_point.y() * scale_y)
            )
            
            painter.setPen(QtGui.QPen(QtCore.Qt.GlobalColor.blue, self.current_line_width, QtCore.Qt.PenStyle.DashLine))
            painter.drawRect(QtCore.QRect(scaled_start, scaled_end))
            
        painter.end()
        self.image_display.setPixmap(scaled_pixmap)

    def _get_crop_color(self, index):
        """为不同裁切区域生成不同颜色"""
        colors = [
            QtCore.Qt.GlobalColor.red,
            QtCore.Qt.GlobalColor.green,
            QtCore.Qt.GlobalColor.blue,
            QtCore.Qt.GlobalColor.magenta,
            QtCore.Qt.GlobalColor.cyan,
            QtCore.Qt.GlobalColor.darkRed,
            QtCore.Qt.GlobalColor.darkGreen,
            QtCore.Qt.GlobalColor.darkBlue
        ]
        return colors[index % len(colors)]

    def on_scroll_area_resize(self, event):
        """窗口大小变化时更新显示"""
        self.update_image_display()
        super(QScrollArea, self.scroll_area).resizeEvent(event)

    def mouse_press_event(self, event):
        """鼠标按下事件"""
        if not self.current_pixmap or self.current_pixmap.isNull():
            return
            
        pos = self._map_to_original_image(event.pos())
        
        # 检查Ctrl键是否按下（移动选框）
        if event.modifiers() & QtCore.Qt.KeyboardModifier.ControlModifier:
            for i, rect in enumerate(reversed(self.crop_regions)):
                if rect.contains(pos):
                    real_index = len(self.crop_regions) - 1 - i
                    self.history.append(("move", real_index, rect))
                    self.moving_crop_index = real_index
                    self.move_offset = pos - rect.topLeft()
                    self.update_image_display()
                    return
        else:
            # 绘制新裁切框
            self.drawing = True
            self.start_point = pos
            self.end_point = pos
            self.update_image_display()

    def mouse_move_event(self, event):
        """鼠标移动事件"""
        if not self.current_pixmap or self.current_pixmap.isNull():
            return
            
        pos = self._map_to_original_image(event.pos())
        
        if self.moving_crop_index >= 0:
            # 移动选框
            current_rect = self.crop_regions[self.moving_crop_index]
            new_pos = pos - self.move_offset
            new_rect = QtCore.QRect(
                new_pos.x(), new_pos.y(),
                current_rect.width(), current_rect.height()
            )
            self.crop_regions[self.moving_crop_index] = new_rect
            self.update_image_display()
            
        elif self.drawing:
            # 绘制裁切框
            self.end_point = pos
            self.update_image_display()

    def mouse_release_event(self, event):
        """鼠标释放事件"""
        if not self.current_pixmap or self.current_pixmap.isNull():
            return
            
        pos = self._map_to_original_image(event.pos())
        
        if self.moving_crop_index >= 0:
            # 完成选框移动
            current_rect = self.crop_regions[self.moving_crop_index]
            new_pos = pos - self.move_offset
            new_rect = QtCore.QRect(
                new_pos.x(), new_pos.y(),
                current_rect.width(), current_rect.height()
            )
            self.crop_regions[self.moving_crop_index] = new_rect
            self.moving_crop_index = -1
            self.update_image_display()
            
        elif self.drawing:
            # 完成裁切框绘制
            self.drawing = False
            self.end_point = pos
            crop_rect = QtCore.QRect(self.start_point, self.end_point).normalized()
            
            if crop_rect.width() > 10 and crop_rect.height() > 10:
                self.history.append(("add", len(self.crop_regions), crop_rect))
                self.crop_regions.append(crop_rect)
                
            self.update_image_display()

    def _map_to_original_image(self, point):
        """将鼠标坐标映射到原始图像坐标"""
        if not self.current_pixmap or self.current_pixmap.isNull():
            return point

        viewport = self.scroll_area.viewport()
        viewport_width = viewport.width()
        viewport_height = viewport.height()
        
        original_width = self.current_pixmap.width()
        original_height = self.current_pixmap.height()
        
        scale_factor = min(viewport_width / original_width, viewport_height / original_height)
        scaled_width = int(original_width * scale_factor)
        scaled_height = int(original_height * scale_factor)
        offset_x = (viewport_width - scaled_width) / 2
        offset_y = (viewport_height - scaled_height) / 2

        if scale_factor > 0:
            original_x = (point.x() - offset_x) / scale_factor
            original_y = (point.y() - offset_y) / scale_factor
        else:
            original_x = point.x()
            original_y = point.y()

        original_x = max(0, min(original_x, original_width - 1))
        original_y = max(0, min(original_y, original_height - 1))

        return QtCore.QPoint(int(original_x), int(original_y))

    # 以下是外部调用的方法
    def set_line_width(self, width):
        """设置线框粗细"""
        self.current_line_width = width
        self.update_image_display()

    def undo_last_action(self):
        """撤销上一步操作"""
        if not self.history:
            return False
            
        action_type, index, data = self.history.pop()
        
        if action_type == "add" and index < len(self.crop_regions):
            self.crop_regions.pop(index)
        elif action_type == "move" and index < len(self.crop_regions):
            self.crop_regions[index] = data
        elif action_type == "clear":
            self.crop_regions = data
            
        self.update_image_display()
        return True

    def clear_all_crops(self):
        """清除所有裁切区域"""
        if self.crop_regions:
            self.history.append(("clear", 0, self.crop_regions.copy()))
        self.crop_regions = []
        self.moving_crop_index = -1
        self.update_image_display()

    def get_crop_regions(self):
        """获取所有裁切区域"""
        return self.crop_regions

    def get_current_pixmap(self):
        """获取当前图像"""
        return self.current_pixmap

    def set_current_image_name(self, name):
        """设置当前图像名称"""
        self.current_image_name = name

    def get_current_image_name(self):
        """获取当前图像名称"""
        return self.current_image_name