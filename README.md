# Image Cutter

一个用于自动识别与裁切漫画分镜的桌面工具。本项目在原有分镜提取能力的基础上进行了二次开发，补充了图片拖放、批量处理、裁切结果预览、手动裁切、缩放和平移等使用体验改进。

## 使用方式

1. 安装项目依赖：`pip install -r requirements.txt`
2. 启动图形界面：`python src/main.py --gui`
3. 将图片拖入图片列表，或选择输入目录与输出目录。
4. 点击“开始自动裁切”，完成后可通过“裁切图片查看”预览结果。

## 致谢

本项目基于 [adenzu/Manga-Panel-Extractor](https://github.com/adenzu/Manga-Panel-Extractor) 进行二次开发。感谢原作者 **adenzu** 提供的漫画分镜提取项目、算法实现与开源基础。

原项目采用 [MIT License](https://github.com/adenzu/Manga-Panel-Extractor/blob/main/LICENSE) 发布；使用、分发或继续修改源自原项目的代码时，请遵守该许可证的条款。

## 说明

分镜检测主要面向漫画页面设计；对于条漫、网漫或特殊排版，识别效果可能因图像内容而异。
