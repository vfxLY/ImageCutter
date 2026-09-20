import os
import cv2
from PyQt6.QtCore import QThread, pyqtSignal
from myutils.myutils import ImageWithFilename, load_image
from image_processing.panel import OutputMode, MergeMode, generate_panel_blocks_by_ai

class ExtractionThread(QThread):
    progress_update = pyqtSignal(int, int)
    process_finished = pyqtSignal()

    def __init__(self, 
                input_dir: str, 
                output_dir: str, 
                image_paths: list[str] | None = None,
                split_joint_panels: bool = False, 
                fallback: bool = False, 
                output_to_folders: bool = False,
                output_mode: int = 0,
                merge_mode: int = 0
                ):
        super().__init__()
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.image_paths = image_paths or []
        self.split_joint_panels = split_joint_panels
        self.fallback = fallback
        self.output_to_folders = output_to_folders
        self.output_mode = OutputMode.from_index(output_mode)
        self.merge_mode = MergeMode.from_index(merge_mode)

    def run(self):
        if self.image_paths:
            image_paths = [path for path in self.image_paths if os.path.isfile(path)]
        else:
            image_paths = [
                os.path.join(self.input_dir, file)
                for file in os.listdir(self.input_dir)
            ]

        total_files = len(image_paths)
        name_counts = {}

        def extract(image: ImageWithFilename, output_folder: str, output_name: str):
            image_name, image_ext = os.path.splitext(image.image_name)
            for k, panel in enumerate(
                generate_panel_blocks_by_ai(
                image.image, 
                merge=self.merge_mode
                )
            ):
                    out_path = os.path.join(output_folder, f"{output_name}_{k}{image_ext}")
                    cv2.imwrite(out_path, panel)

        for i, image_path in enumerate(image_paths):
            if self.isInterruptionRequested():
                break
            self.progress_update.emit(i + 1, total_files)
            file = os.path.basename(image_path)
            image_name, _ = os.path.splitext(file)
            name_counts[image_name] = name_counts.get(image_name, 0) + 1
            output_name = image_name if name_counts[image_name] == 1 else f"{image_name}_{name_counts[image_name]}"
            output_folder = self.output_dir
            if self.output_to_folders:
                output_folder = os.path.join(self.output_dir, output_name)
                if not os.path.exists(output_folder):
                    os.makedirs(output_folder)
            image = load_image(os.path.dirname(image_path), file)
            if image.image is not None:
                extract(image, output_folder, output_name)

        self.process_finished.emit()
