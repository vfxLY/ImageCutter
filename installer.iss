[Setup]
AppName=漫画切割器
AppVersion=1.0
DefaultDirName={userappdata}\MangaCutter
DefaultGroupName=漫画切割器
OutputDir=output
OutputBaseFilename=manga_cutter_setup
SetupIconFile=icon.ico

[Files]
Source: "ImageCutterr\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs
Source: "launcher.bat"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\漫画切割器"; Filename: "{app}\launcher.bat"
Name: "{commondesktop}\漫画切割器"; Filename: "{app}\launcher.bat"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "附加任务:"