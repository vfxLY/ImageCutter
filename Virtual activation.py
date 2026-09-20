#python -m venv myenv
#myenv\Scripts\activate

#python src/main.py  /// /���г���
#pyinstaller main.spec/////pyinstaller --onefile --windowed --icon=icon.ico src/main.py

import yolov5

# ֱ�Ӵӱ��ؾ���·������
model = yolov5.load('F:/AIGC/ImageCutterr2/yolov5_weights/yolov5s.pt')
print("ģ�ͼ��سɹ�")   yolov5s.pt
model_path = "F:/AIGC/ImageCutterr2/yolov5_weights/yolov5s.pt"



nuitka --standalone --onefile ^
  --enable-plugin=pyqt6 ^
  --module-parameter=torch-disable-jit=yes ^
  --noinclude-setuptools-mode=warning ^
  --include-package=gui ^
  --include-package=image_processing ^
  --include-package=ultralytics ^
  --include-data-files="src/ai-models/2024-11-00/best.pt=ai-models/2024-11-00/best.pt" ^
  --include-data-files="yolov5_weights/*.pt=yolov5_weights/" ^
  src/main.py

  nuitka --standalone ^
--include-package=yolov5 ^
--include-package=torch ^
--include-package=ultralytics ^
--include-package=cv2 ^
--include-data-dir="C:\Users\DELL\AppData\Local\Programs\Python\Python310\lib\site-packages\cv2=cv2" ^
--include-data-dir=yolov5_weights=yolov5_weights ^
--output-dir=dist ^
src/main.py  # 替换为你的实际文件名

nuitka --standalone --enable-plugin=pyqt6 --enable-plugin=tk-inter --disable-plugin=anti-bloat --include-package=yolov5 --include-package=torch --include-package=ultralytics --include-package=cv2 --include-package=streamlit --include-data-dir="C:\Users\DELL\AppData\Local\Programs\Python\Python310\lib\site-packages\cv2=cv2" --include-data-dir=yolov5_weights=yolov5_weights --output-dir=dist src/main.py

nuitka --standalone --onefile --enable-plugin=pyqt6 --module-parameter=torch-disable-jit=yes --noinclude-setuptools-mode=warning --include-package=gui --include-package=image_processing --include-package=yolov5 --include-data-files="src/ai-models/2024-11-00/best.pt=ai-models/2024-11-00/best.pt" --include-data-files="yolov5_weights/*.pt=yolov5_weights/" src/main.py

(nuitka --standalone--onefile--enable-plugin)=pyqt6 --module-parameter=torch-disable-jit=yes --noinclude-setuptools-mode=warning --include-package=gui --include-package=image_processing --include-package=yolov5--include-data-files="src/ai-models/2024-11-00/best.pt=ai-models/2024-11-00/best.pt" --include-data-files="yolov5_weights/*.pt=yolov5_weights/" src/main.py




nuitka --onefile ^
--enable-plugin=pyqt6 ^
--include-data-file="C:\Users\DELL\AppData\Local\Programs\Python\Python310\Lib\site-packages\PyQt6\Qt6\plugins\platforms\qwindows.dll=platforms/qwindows.dll" ^
--module-parameter=torch-disable-jit=yes ^
main.py



nuitka --onefile ^
--enable-plugin=pyqt6 ^
--include-data-file="C:\Users\DELL\AppData\Local\Programs\Python\Python310\Lib\site-packages\PyQt6\Qt6\plugins\platforms\qwindows.dll=platforms/qwindows.dll" ^
--module-parameter=torch-disable-jit=yes ^
--exclude-module=PyQt5 --exclude-module=PyQt5.sip ^
main.py




nuitka --onefile ^
--enable-plugin=pyqt6 ^
--include-data-file="C:\Users\DELL\AppData\Local\Programs\Python\Python311\Lib\site-packages\PyQt6\Qt6\plugins\platforms\qwindows.dll=platforms/qwindows.dll" ^
--module-parameter=torch-disable-jit=yes ^
F:\AIGC\ImageCutter\src\main.py



nuitka --onefile ^
--enable-plugin=pyqt6 ^
--include-data-file="C:\Users\DELL\AppData\Local\Programs\Python\Python311\Lib\site-packages\PyQt6\Qt6\plugins\platforms\qwindows.dll=platforms/qwindows.dll" ^
--module-parameter=torch-disable-jit=yes ^
--include-module=cv2 ^
F:\AIGC\ImageCutter\src\main.py








nuitka --onefile ^
--enable-plugin=pyqt6 ^
--include-data-file="C:\Users\DELL\AppData\Local\Programs\Python\Python311\Lib\site-packages\PyQt6\Qt6\plugins\platforms\qwindows.dll=platforms/qwindows.dll" ^
--include-data-file="F:\AIGC\ImageCutter\src\ai-models\2024-11-00\best.pt=ai-models\2024-11-00\best.pt" ^
--module-parameter=torch-disable-jit=yes ^
--include-module=cv2 ^
--include-module=tqdm ^
--include-module=requests ^
--include-module=torch ^
--include-module=torch._C ^
--include-module=torch.nn ^
--include-module=torch.utils ^
--include-module=torchvision ^
--include-module=ultralytics ^
--include-data-dir="C:\Users\DELL\AppData\Local\Programs\Python\Python311\Lib\site-packages\ultralytics=ultralytics" ^
--include-module=logging ^
--include-module=logging.config ^
--include-module=seaborn ^
--plugin-no-detection ^
F:\AIGC\ImageCutter\src\main.py







nuitka --onefile ^
--enable-plugin=pyqt6 ^
--include-data-file="C:\Users\DELL\AppData\Local\Programs\Python\Python311\Lib\site-packages\PyQt6\Qt6\plugins\platforms\qwindows.dll=platforms/qwindows.dll" ^
--include-data-file="F:\AIGC\ImageCutter\src\ai-models\2024-11-00\best.pt=ai-models\2024-11-00\best.pt" ^
--module-parameter=torch-disable-jit=yes ^
--include-module=cv2 ^
--include-module=tqdm ^
--include-module=requests ^
--include-module=torch ^
--include-module=torch._C ^
--include-module=torch.nn ^
--include-module=torch.utils ^
--include-module=torchvision ^
--include-module=ultralytics ^
--include-data-dir="C:\Users\DELL\AppData\Local\Programs\Python\Python311\Lib\site-packages\ultralytics=ultralytics" ^
--include-module=logging ^
--include-module=logging.config ^
--include-module=seaborn ^
--plugin-no-detection ^
--windows-icon-from-ico="F:\AIGC\ImageCutter\icon.ico" ^
F:\AIGC\ImageCutter\src\main.py