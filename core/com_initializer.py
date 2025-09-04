#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
COM组件初始化模块
用于在程序启动时自动清理和初始化COM组件，确保Excel相关操作正常
"""

import os
import sys
import shutil
import subprocess
import tempfile
import logging
from pathlib import Path

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class COMInitializer:
    """COM组件初始化器"""
    
    def __init__(self):
        self.cleaned_paths = []
        self.excel_registered = False
        
    def initialize(self):
        """完整的COM组件初始化流程"""
        try:
            logger.info("开始COM组件初始化流程...")
            
            # 1. 清理COM组件缓存（必需）
            if self.clean_com_cache():
                logger.info("✅ COM组件缓存清理完成")
            else:
                logger.warning("⚠️ COM组件缓存清理失败")
            
            # 2. 尝试注册Excel COM组件（可选）
            try:
                if self.register_excel_com():
                    logger.info("✅ Excel COM组件注册成功")
                    self.excel_registered = True
                else:
                    logger.warning("⚠️ Excel COM组件注册失败，但程序仍可运行")
                    self.excel_registered = False
            except Exception as e:
                logger.warning(f"⚠️ Excel注册过程出错，跳过注册: {e}")
                self.excel_registered = False
            
            # 3. 验证COM组件状态
            self.verify_com_status()
            
            logger.info("COM组件初始化流程完成")
            return True  # 即使Excel注册失败，也返回True
            
        except Exception as e:
            logger.error(f"❌ COM组件初始化失败: {e}")
            return False
    
    def clean_com_cache(self):
        """清理COM组件缓存"""
        logger.info("开始清理COM组件缓存...")
        
        try:
            # 1. 清理Python安装目录下的gen_py
            python_paths = [
                os.path.dirname(sys.executable),
                os.path.join(os.path.dirname(sys.executable), 'Lib', 'site-packages'),
                os.path.join(os.path.dirname(sys.executable), 'Lib', 'site-packages', 'win32com'),
            ]
            
            for base_path in python_paths:
                gen_py_path = os.path.join(base_path, 'gen_py')
                if os.path.exists(gen_py_path):
                    try:
                        shutil.rmtree(gen_py_path)
                        self.cleaned_paths.append(gen_py_path)
                        logger.info(f"✅ 已清理: {gen_py_path}")
                    except Exception as e:
                        logger.warning(f"⚠️ 清理失败: {gen_py_path} - {e}")
            
            # 2. 清理临时目录下的COM缓存
            temp_dirs = [
                os.environ.get('TEMP', ''),
                os.environ.get('TMP', ''),
                tempfile.gettempdir(),
            ]
            
            for temp_dir in temp_dirs:
                if temp_dir and os.path.exists(temp_dir):
                    com_cache_path = os.path.join(temp_dir, 'gen_py')
                    if os.path.exists(com_cache_path):
                        try:
                            shutil.rmtree(com_cache_path)
                            self.cleaned_paths.append(com_cache_path)
                            logger.info(f"✅ 已清理: {com_cache_path}")
                        except Exception as e:
                            logger.warning(f"⚠️ 清理失败: {com_cache_path} - {e}")
            
            # 3. 清理用户目录下的COM缓存
            user_profile = os.environ.get('USERPROFILE', '')
            if user_profile:
                user_com_cache = os.path.join(user_profile, 'AppData', 'Local', 'Temp', 'gen_py')
                if os.path.exists(user_com_cache):
                    try:
                        shutil.rmtree(user_com_cache)
                        self.cleaned_paths.append(user_com_cache)
                        logger.info(f"✅ 已清理: {user_com_cache}")
                    except Exception as e:
                        logger.warning(f"⚠️ 清理失败: {user_com_cache} - {e}")
            
            if self.cleaned_paths:
                logger.info(f"✅ COM组件缓存清理完成，共清理 {len(self.cleaned_paths)} 个目录")
                return True
            else:
                logger.info("ℹ️ 未找到需要清理的COM缓存目录")
                return True
                
        except Exception as e:
            logger.error(f"❌ 清理COM缓存时出错: {e}")
            return False
    
    def register_excel_com(self):
        """尝试注册Excel COM组件"""
        logger.info("尝试注册Excel COM组件...")
        
        excel_paths = [
            r"C:\Program Files\Microsoft Office\root\Office16\EXCEL.EXE",
            r"C:\Program Files (x86)\Microsoft Office\root\Office16\EXCEL.EXE",
            r"C:\Program Files\Microsoft Office\Office16\EXCEL.EXE",
            r"C:\Program Files (x86)\Microsoft Office\Office16\EXCEL.EXE",
            r"C:\Program Files\Microsoft Office\root\Office15\EXCEL.EXE",
            r"C:\Program Files (x86)\Microsoft Office\root\Office15\EXCEL.EXE",
            r"C:\Program Files\Microsoft Office\root\Office14\EXCEL.EXE",
            r"C:\Program Files (x86)\Microsoft Office\root\Office14\EXCEL.EXE",
        ]
        
        for excel_path in excel_paths:
            if os.path.exists(excel_path):
                try:
                    logger.info(f"找到Excel: {excel_path}")
                    result = subprocess.run([excel_path, "/register"], 
                                          capture_output=True, text=True, timeout=30)
                    if result.returncode == 0:
                        logger.info("✅ Excel COM组件注册成功")
                        return True
                    else:
                        logger.warning(f"⚠️ Excel注册失败: {result.stderr}")
                except Exception as e:
                    logger.warning(f"⚠️ 注册Excel时出错: {e}")
        
        logger.error("❌ 未找到Excel或注册失败")
        return False
    
    def verify_com_status(self):
        """验证COM组件状态"""
        logger.info("验证COM组件状态...")
        
        try:
            # 尝试导入win32com
            import win32com.client
            logger.info("✅ win32com模块可用")
            
            # 尝试创建Excel应用对象
            try:
                excel_app = win32com.client.Dispatch("Excel.Application")
                excel_app.Quit()
                logger.info("✅ Excel COM组件可用")
            except Exception as e:
                logger.warning(f"⚠️ Excel COM组件不可用: {e}")
                
        except ImportError:
            logger.warning("⚠️ win32com模块不可用")
        
        # 检查xlwings
        try:
            import xlwings as xw
            logger.info("✅ xlwings模块可用")
        except ImportError:
            logger.warning("⚠️ xlwings模块不可用")
    
    def get_status_summary(self):
        """获取初始化状态摘要"""
        return {
            "cleaned_paths_count": len(self.cleaned_paths),
            "excel_registered": self.excel_registered,
            "cleaned_paths": self.cleaned_paths
        }

def initialize_com_components():
    """便捷的初始化函数"""
    initializer = COMInitializer()
    success = initializer.initialize()
    return success, initializer.get_status_summary()

if __name__ == "__main__":
    # 测试模式
    print("=" * 50)
    print("    COM组件初始化器测试")
    print("=" * 50)
    
    success, status = initialize_com_components()
    
    print(f"\n初始化结果: {'成功' if success else '失败'}")
    print(f"清理路径数量: {status['cleaned_paths_count']}")
    print(f"Excel注册状态: {'成功' if status['excel_registered'] else '失败'}")
    
    if status['cleaned_paths']:
        print("\n清理的路径:")
        for path in status['cleaned_paths']:
            print(f"  - {path}")
    
    print("\n" + "=" * 50)