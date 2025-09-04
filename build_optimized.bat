@echo off
chcp 65001 >nul
echo ========================================
echo    验收测试报告生成工具 - 打包脚本
echo ========================================

REM 检查Python环境
echo [1/6] 检查Python环境...
python --version >nul 2>&1
if errorlevel 1 (
    echo 错误: 未找到Python环境
    pause
    exit /b 1
)
echo Python环境正常

REM 检查PyInstaller
echo [2/6] 检查PyInstaller...
python -c "import PyInstaller" >nul 2>&1
if errorlevel 1 (
    echo 安装PyInstaller...
    python -m pip install pyinstaller
    if errorlevel 1 (
        echo PyInstaller安装失败
        pause
        exit /b 1
    )
)
echo PyInstaller已安装

REM 创建程序图标
echo [3/6] 创建程序图标...
python create_icon.py
if errorlevel 1 (
    echo 图标创建失败
    pause
    exit /b 1
)
echo 程序图标已创建


REM 清理COM组件缓存
echo [3.5/6] 清理COM组件缓存...
python cleanup_com_cache.py
if errorlevel 1 (
    echo COM缓存清理失败，但继续打包
)
echo COM缓存清理完成

REM 清理之前的构建
echo [4/6] 清理之前的构建...
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"
echo 清理完成

REM 执行打包
echo [5/6] 开始打包...
python -m PyInstaller build_optimized.spec --clean
if errorlevel 1 (
    echo 打包失败
    pause
    exit /b 1
)
echo 打包完成

REM 复制外部文件到dist目录
echo [6/6] 复制外部文件...

REM 查找实际的exe文件位置
set "EXE_FOUND="
for /d %%i in ("dist\*") do (
    if exist "%%i\验收测试报告生成工具.exe" (
        set "TARGET_DIR=%%i"
        set "EXE_FOUND=1"
        goto :found_exe
    )
)

:found_exe
if not defined EXE_FOUND (
    echo 错误: 未找到打包后的exe文件
    pause
    exit /b 1
)

echo 找到目标目录: %TARGET_DIR%

REM 复制配置文件
echo 复制配置文件...
copy "*.ini" "%TARGET_DIR%\" >nul 2>&1

REM 复制数据目录
echo 复制数据目录...
if exist "raw_data" (
    xcopy "raw_data" "%TARGET_DIR%\raw_data\" /E /I /Y >nul 2>&1
    echo - raw_data 已复制
)
if exist "reference" (
    xcopy "reference" "%TARGET_DIR%\reference\" /E /I /Y >nul 2>&1
    echo - reference 已复制
)
if exist "taizhang" (
    xcopy "taizhang" "%TARGET_DIR%\taizhang\" /E /I /Y >nul 2>&1
    echo - taizhang 已复制
)
if exist "logs" (
    xcopy "logs" "%TARGET_DIR%\logs\" /E /I /Y >nul 2>&1
    echo - logs 已复制
)

echo 外部文件复制完成

REM 检查打包结果
if exist "%TARGET_DIR%\验收测试报告生成工具.exe" (
    echo.
    echo ========================================
    echo           打包成功！
    echo ========================================
    echo 程序位置: %TARGET_DIR%
    echo 主程序: 验收测试报告生成工具.exe
    echo 数据目录: raw_data, reference, taizhang, logs
    echo 配置文件: *.ini
    echo.
    echo 提示: 外部文件已复制到程序目录，方便更新
    echo.

    REM 显示目录内容
    echo 目录内容:
    dir "%TARGET_DIR%" /B
    echo.
) else (
    echo 打包失败！
)

pause