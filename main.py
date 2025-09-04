import sys
from PyQt5.QtWidgets import QApplication
from ui.main_window import MainApplication
import os

# 设置环境变量，防止COM组件自动生成
os.environ["PYTHONCOM_NO_GENERATE"] = "1"

def setup_com_components():
    """初始化COM组件，清理缓存并注册Excel COM组件"""
    try:
        print("正在初始化COM组件...")
        
        # 使用新的COM组件初始化模块
        from core.com_initializer import initialize_com_components as init_com
        
        success, status = init_com()
        
        if success:
            print("✅ COM组件初始化完成")
            print(f"清理路径数量: {status['cleaned_paths_count']}")
            print(f"Excel注册状态: {'成功' if status['excel_registered'] else '失败'}")
        else:
            print("⚠️ COM组件初始化失败")
            
        return success
        
    except Exception as e:
        print(f"❌ COM组件初始化失败: {e}")
        return False

if __name__ == "__main__":
    # 在创建QApplication之前初始化COM组件
    print("=" * 50)
    print("    XD_自动化报告生成工具_V2.0")
    print("=" * 50)
    
    # 初始化COM组件
    setup_com_components()
    
    print("\n正在启动应用程序...")
    
    app = QApplication(sys.argv)
    window = MainApplication()
    window.show()
    sys.exit(app.exec_())