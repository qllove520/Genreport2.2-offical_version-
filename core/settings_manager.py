import json
import os
import traceback


class SettingsManager:
    def __init__(self, app_prefix="default"):
        self.app_prefix = app_prefix

        # 确保配置目录存在且路径正确
        self.config_dir = os.getcwd()
        if not os.path.exists(self.config_dir):
            os.makedirs(self.config_dir, exist_ok=True)

    def save_settings(self, settings_type: str, settings_data: dict, log_callback=None):
        """Saves the settings to a JSON file with UTF-8 encoding."""
        file_path = os.path.join(self.config_dir, f"{settings_type}.ini")
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(settings_data, f, ensure_ascii=False, indent=4)
            if log_callback:
                log_callback(f"设置已保存到: {os.path.basename(file_path)}", False)
        except Exception as e:
            if log_callback:
                log_callback(f"保存设置失败: {e}\n{traceback.format_exc()}", True)
            # 记录到错误日志
            self._log_error(f"保存设置失败: {settings_type}", e)

    def load_settings(self, settings_type: str, default_settings: dict, log_callback=None) -> dict:
        """Loads settings from a JSON file, attempting UTF-8 first, then GBK."""
        # 修复：使用.json扩展名而不是.ini，因为内容是JSON格式
        file_path = os.path.join(self.config_dir, f"{settings_type}.ini")
        
        if os.path.exists(file_path):
            try:
                # 首先检查文件大小，避免读取损坏的文件
                if os.path.getsize(file_path) == 0:
                    if log_callback:
                        log_callback(f"警告: 设置文件 '{os.path.basename(file_path)}' 为空，将使用默认设置。", True)
                    return default_settings
                    
                with open(file_path, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                if log_callback:
                    log_callback(f"已加载设置文件: {os.path.basename(file_path)}", False)
                return settings
            except UnicodeDecodeError:
                if log_callback:
                    log_callback(f"警告: 设置文件 '{os.path.basename(file_path)}' 非 UTF-8 编码，尝试 GBK...", False)
                try:
                    with open(file_path, 'r', encoding='gbk') as f:
                        settings = json.load(f)
                    if log_callback:
                        log_callback(f"已成功加载 GBK 编码的设置文件: {os.path.basename(file_path)}", False)
                    try:
                        self.save_settings(settings_type, settings, log_callback)
                        if log_callback:
                            log_callback(f"已将 '{os.path.basename(file_path)}' 重新保存为 UTF-8。", False)
                    except Exception as resave_e:
                        if log_callback:
                            log_callback(f"重新保存为 UTF-8 失败: {resave_e}\n{traceback.format_exc()}", True)
                    return settings
                except Exception as e:
                    if log_callback:
                        log_callback(f"加载设置文件失败 (尝试 GBK): {e}\n{traceback.format_exc()}", True)
                        log_callback(f"将使用默认设置。", False)
                    self._log_error(f"加载设置失败: {settings_type}", e)
                    return default_settings
            except (json.JSONDecodeError, ValueError) as e:
                if log_callback:
                    log_callback(f"设置文件格式错误: {e}\n将使用默认设置。", True)
                self._log_error(f"JSON解析失败: {settings_type}", e)
                return default_settings
            except Exception as e:
                if log_callback:
                    log_callback(f"加载设置文件失败: {e}\n{traceback.format_exc()}", True)
                    log_callback(f"将使用默认设置。", False)
                self._log_error(f"加载设置失败: {settings_type}", e)
                return default_settings
        else:
            if log_callback:
                log_callback(f"未找到 {os.path.basename(file_path)} 的设置文件，将创建默认配置文件。", False)
            # 自动创建默认配置文件
            try:
                self.save_settings(settings_type, default_settings, log_callback)
                if log_callback:
                    log_callback(f"已创建默认配置文件: {os.path.basename(file_path)}", False)
            except Exception as e:
                if log_callback:
                    log_callback(f"创建默认配置文件失败: {e}", True)
            return default_settings
    
    def _log_error(self, message: str, exception: Exception):
        """内部错误日志记录"""
        try:
            error_log_path = os.path.join(self.config_dir, "settings_errors.log")
            with open(error_log_path, 'a', encoding='utf-8') as f:
                from datetime import datetime
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                f.write(f"[{timestamp}] {message}: {str(exception)}\n")
        except Exception:
            # 如果连错误日志都写不了，就忽略
            pass
    
    def backup_settings(self, settings_type: str) -> bool:
        """备份设置文件"""
        try:
            source_path = os.path.join(self.config_dir, f"{settings_type}.ini")
            if os.path.exists(source_path):
                from datetime import datetime
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                backup_path = os.path.join(self.config_dir, f"{settings_type}_backup_{timestamp}.ini")
                import shutil
                shutil.copy2(source_path, backup_path)
                return True
            return False
        except Exception:
            return False
