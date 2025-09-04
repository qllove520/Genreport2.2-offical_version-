# ui/zentao_export_page.py - 修改后的禅道导出页面

import os
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,QComboBox,
    QLineEdit, QPushButton, QTextEdit, QFileDialog, QMessageBox, QProgressDialog, QGroupBox, QCheckBox
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QTextCharFormat, QColor, QTextCursor
from datetime import datetime

from core.selenium_worker import SeleniumWorker
from core.settings_manager import SettingsManager
from config.settings import DOWNLOAD_DIR, HEADLESS_MODE_DEFAULT, TEST_REPORT_ID_DEFAULT


class ZentaoExportPage(QWidget):
    # 新增信号：用户登录成功
    user_logged_in = pyqtSignal(object)  # 传递用户信息对象

    def __init__(self, parent=None):
        super().__init__(parent)
        self.worker_thread = None
        self.progress_dialog = None
        self.settings_manager = SettingsManager("zentao_export")
        self.current_user_info = None  # 存储当前用户信息

        self.init_ui()
        self.load_settings()

    def init_ui(self):
        main_layout = QVBoxLayout(self)

        # 禅道登录信息 GroupBox
        login_group_box = QGroupBox("禅道登录信息")
        login_group_box.setStyleSheet("""
            QGroupBox {
                font-size: 16px;
                font-weight: bold;
                border: 2px solid #4CAF50;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 5px;
                left: 10px;
                color: #4CAF50;
            }
        """)
        login_layout = QVBoxLayout()

        self.account_input = self._create_input_field(login_layout, "账号:", "")
        self.account_input.setPlaceholderText("请输入禅道账号")
        self.account_input.setStyleSheet("""
            QLineEdit {
                padding: 8px;
                border: 1px solid #ccc;
                border-radius: 5px;
                font-size: 14px;
            }
            QLineEdit:focus {
                border: 1px solid #4CAF50;
            }
        """)

        self.password_input = self._create_input_field(login_layout, "密码:", "", is_password=True)
        self.password_input.setPlaceholderText("请输入禅道密码")
        self.password_input.setStyleSheet("""
            QLineEdit {
                padding: 8px;
                border: 1px solid #ccc;
                border-radius: 5px;
                font-size: 14px;
            }
            QLineEdit:focus {
                border: 1px solid #4CAF50;
            }
        """)

        # 新增登录测试按钮
        login_test_layout = QHBoxLayout()
        self.test_login_btn = QPushButton("登录并获取用户信息")
        self.test_login_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border-radius: 5px;
                font-size: 14px;
                padding: 8px 15px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #39843c;
            }
        """)
        self.test_login_btn.clicked.connect(self._test_login)
        self.test_login_btn.setFixedHeight(30)
        login_test_layout.addWidget(self.test_login_btn)
        login_test_layout.addStretch()
        login_layout.addLayout(login_test_layout)

        # 无头模式复选框
        self.headless_checkbox = QCheckBox("无头模式 (不显示浏览器界面)")
        self.headless_checkbox.setChecked(HEADLESS_MODE_DEFAULT)
        login_layout.addWidget(self.headless_checkbox)

        login_group_box.setLayout(login_layout)
        main_layout.addWidget(login_group_box)

        # 全局参数设置 GroupBox
        global_settings_group_box = QGroupBox("全局参数设置")
        global_settings_group_box.setStyleSheet("""
            QGroupBox {
                font-size: 16px;
                font-weight: bold;
                border: 2px solid #2196F3;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 5px;
                left: 10px;
                color: #2196F3;
            }
        """)
        global_settings_layout = QVBoxLayout()

        self.product_name_input = self._create_input_field(global_settings_layout, "产品名称:", "")
        self.product_name_input.setPlaceholderText("请输入唯一产品名称关键字，例如\"7891K1\",7891不行太多产品名称包含了（必须是整个产品列表中的唯一关键字）")
        self.product_name_input.setStyleSheet("""
            QLineEdit {
                padding: 8px;
                border: 1px solid #ccc;
                border-radius: 5px;
                font-size: 14px;
            }
            QLineEdit:focus {
                border: 1px solid #2196F3;
            }
        """)

        self.project_name_input = self._create_input_field(global_settings_layout, "项目名称:", "")
        self.project_name_input.setPlaceholderText("请输入项目名称唯一关键字，例如\"9988_北京亦庄工程\",（必须是整个项目列表中的唯一关键字）")
        self.project_name_input.setStyleSheet("""
            QLineEdit {
                padding: 8px;
                border: 1px solid #ccc;
                border-radius: 5px;
                font-size: 14px;
            }
            QLineEdit:focus {
                border: 1px solid #2196F3;
            }
        """)

        # 测试单号输入框和保存按钮
        test_report_id_layout = QHBoxLayout()
        self.test_report_id_label = QLabel("测试单号:")
        self.test_report_id_input = QLineEdit(TEST_REPORT_ID_DEFAULT)
        self.test_report_id_input.setPlaceholderText("请输入测试单号，例如\"CSSQ20250530001\"")
        self.test_report_id_input.setStyleSheet("""
            QLineEdit {
                padding: 8px;
                border: 1px solid #ccc;
                border-radius: 5px;
                font-size: 14px;
            }
            QLineEdit:focus {
                border: 1px solid #2196F3;
            }
        """)
        self.save_test_report_id_button = QPushButton("保存测试单号")
        self.save_test_report_id_button.clicked.connect(self._save_test_report_id)
        self.save_test_report_id_button.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border-radius: 5px;
                font-size: 14px;
                padding: 8px 15px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:pressed {
                background-color: #1565C0;
            }
        """)
        test_report_id_layout.addWidget(self.test_report_id_label)
        test_report_id_layout.addWidget(self.test_report_id_input)
        test_report_id_layout.addWidget(self.save_test_report_id_button)
        global_settings_layout.addLayout(test_report_id_layout)
        # 指派人标签和下拉框
        assigned_layout = QHBoxLayout()

        assigned_label = QLabel("指派给:")
        assigned_layout.addWidget(assigned_label)

        self.assigned_combo = QComboBox()
        self.assigned_combo.setEditable(True)
        self.assigned_combo.addItems([
            "张诗婉", "徐芬", "江信辉", "周雪波", "袁超凡", "朱双彬", "何琪", "刘雨鑫", "邱国祥", ""
        ])
        self.assigned_combo.setCurrentText("")  # 默认空白
        self.assigned_combo.setMinimumHeight(32)
        self.assigned_combo.setFixedWidth(140)
        self.assigned_combo.currentTextChanged.connect(self._on_query_conditions_changed)
        self.assigned_combo.setStyleSheet("""
            QLineEdit {
                padding: 8px;
                border: 1px solid #ccc;
                border-radius: 5px;
                font-size: 14px;
            }
            QLineEdit:focus {
                border: 1px solid #2196F3;
            }
        """)
        assigned_layout.addWidget(self.assigned_combo)

        # 添加指派人布局到全局参数设置布局
        global_settings_layout.addLayout(assigned_layout)
        # 下载目录
        download_dir_layout = QHBoxLayout()
        self.download_dir_label = QLabel("下载目录:")
        self.download_dir_display = QLineEdit(DOWNLOAD_DIR)
        self.download_dir_display.setReadOnly(True)
        self.download_dir_display.setStyleSheet("""
            QLineEdit {
                padding: 8px;
                border: 1px solid #ccc;
                border-radius: 5px;
                font-size: 14px;
                background-color: #f5f5f5;
            }
        """)
        self.browse_button = QPushButton("浏览...")
        self.browse_button.clicked.connect(self._browse_download_dir)
        self.browse_button.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border-radius: 5px;
                font-size: 14px;
                padding: 8px 15px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:pressed {
                background-color: #1565C0;
            }
        """)
        download_dir_layout.addWidget(self.download_dir_label)
        download_dir_layout.addWidget(self.download_dir_display)
        download_dir_layout.addWidget(self.browse_button)
        global_settings_layout.addLayout(download_dir_layout)

        global_settings_group_box.setLayout(global_settings_layout)
        main_layout.addWidget(global_settings_group_box)

        # 操作按钮区域
        button_layout = QHBoxLayout()

        # 开始导出按钮
        self.export_button = QPushButton("开始导出")
        self.export_button.setFixedHeight(40)
        self.export_button.clicked.connect(self._start_export)
        self.export_button.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                border-radius: 5px;
                font-size: 16px;
                font-weight: bold;
                padding: 10px 20px;
            }
            QPushButton:hover {
                background-color: #FB8C00;
            }
            QPushButton:pressed {
                background-color: #F57C00;
            }
        """)
        button_layout.addWidget(self.export_button)

        # 刷新用户信息按钮
        self.refresh_user_btn = QPushButton("刷新用户信息")
        self.refresh_user_btn.setFixedHeight(40)
        self.refresh_user_btn.clicked.connect(self.refresh_user_info)
        self.refresh_user_btn.setEnabled(False)  # 默认禁用
        self.refresh_user_btn.setStyleSheet("""
            QPushButton {
                background-color: #9E9E9E;
                color: white;
                border-radius: 5px;
                font-size: 16px;
                font-weight: bold;
                padding: 10px 20px;
            }
            QPushButton:hover {
                background-color: #757575;
            }
            QPushButton:pressed {
                background-color: #616161;
            }
            QPushButton:disabled {
                background-color: #BDBDBD;
                color: #E0E0E0;
            }
        """)
        button_layout.addWidget(self.refresh_user_btn)

        main_layout.addLayout(button_layout)

        # 日志输出区域
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setStyleSheet("""
            QTextEdit {
                background-color: #f8f8f8;
                color: #333;
                font-family: 'Consolas', 'Monospace';
                border: 1px solid #ddd;
                border-radius: 5px;
                padding: 10px;
            }
        """)
        main_layout.addWidget(self.log_output)

    def _create_input_field(self, layout, label_text, default_text="", is_password=False):
        """Helper to create labeled input fields."""
        h_layout = QHBoxLayout()
        label = QLabel(label_text)
        line_edit = QLineEdit(default_text)
        if is_password:
            line_edit.setEchoMode(QLineEdit.Password)
        h_layout.addWidget(label)
        h_layout.addWidget(line_edit)
        layout.addLayout(h_layout)
        return line_edit

    def _on_query_conditions_changed(self, text):
        # 这里可以写你想要的逻辑，比如刷新查询条件等
        self.update_log(f"指派人选择变更为: {text}", False)
        assgined_to = self.assigned_combo.currentText().strip()
        return assgined_to

    def _browse_download_dir(self):
        """Opens a dialog to select the download directory."""
        initial_dir = self.download_dir_display.text()
        if not os.path.isdir(initial_dir):
            initial_dir = os.path.expanduser("~")

        directory = QFileDialog.getExistingDirectory(self, "选择下载目录", initial_dir)
        if directory:
            self.download_dir_display.setText(directory)
            self.save_settings()
            self.update_log(f"已选择下载目录: {directory}", False)

    def _save_test_report_id(self):
        """Saves the test report ID when the button is clicked."""
        self.save_settings()
        QMessageBox.information(self, "保存成功", "测试单号已保存。")
        self.update_log("测试单号已保存。", False)

    def _test_login(self):
        """测试登录并获取用户信息"""
        account = self.account_input.text().strip()
        password = self.password_input.text().strip()

        if not account or not password:
            QMessageBox.warning(self, "输入错误", "请填写账号和密码")
            return

        # 重置取消标志
        if hasattr(self, '_login_cancelled'):
            delattr(self, '_login_cancelled')

        self.log_output.clear()
        self.update_log("--- 开始登录 ---", False)
        self.test_login_btn.setEnabled(False)

        # 创建进度对话框 - 改进设置以避免误触发取消信号
        self.progress_dialog = QProgressDialog("正在登录并获取用户信息...", "取消", 0, 100, self)
        self.progress_dialog.setWindowTitle("登录中")
        self.progress_dialog.setWindowModality(Qt.WindowModal)
        self.progress_dialog.setMinimumDuration(0)
        self.progress_dialog.setAutoClose(False)  # 防止自动关闭
        self.progress_dialog.setAutoReset(False)  # 防止自动重置
        self.progress_dialog.setValue(0)
        self.progress_dialog.show()

        # 创建只用于登录的工作线程
        download_dir = self.download_dir_display.text().strip()
        self.worker_thread = SeleniumWorker(
            account, password, "", "","", "", download_dir,
            self.headless_checkbox.isChecked(),
            task_type="login_only"  # 只登录，不执行导出
        )

        # 连接信号
        self.worker_thread.log_signal.connect(self.update_log)
        self.worker_thread.finished_signal.connect(self._login_test_finished)
        self.worker_thread.progress_signal.connect(self.progress_dialog.setValue)
        self.worker_thread.user_info_signal.connect(self._on_user_info_received)
        self.progress_dialog.canceled.connect(self._cancel_login_test)

        self.worker_thread.start()

    def _login_test_finished(self, success, message):
        """登录测试完成处理"""
        self.test_login_btn.setEnabled(True)
        
        # 安全地关闭进度对话框
        if self.progress_dialog:
            try:
                # 断开取消信号连接，避免误触发
                self.progress_dialog.canceled.disconnect()
                self.progress_dialog.close()
            except:
                pass
            self.progress_dialog = None

        self.update_log(f"\n--- 登录状态: {'成功' if success else '失败'} ---", False)
        self.update_log(message, not success)

        if success:
            QMessageBox.information(self, "登录成功", "登录成功，用户信息已获取")
            self.refresh_user_btn.setEnabled(True)
        else:
            QMessageBox.critical(self, "登录失败", message)

        # 确保线程资源清理
        if self.worker_thread:
            try:
                self.worker_thread.quit()
                self.worker_thread.wait(1000)  # 等待1秒
            except Exception as e:
                self.update_log(f"清理线程资源时出错: {e}", True)
            self.worker_thread = None

    def _on_user_info_received(self, user_info):
        """接收到用户信息"""
        self.current_user_info = user_info
        self.update_log(f"用户信息已获取: {user_info.real_name} ({user_info.account})", False)

        # 发射用户登录信号，通知主窗口
        self.user_logged_in.emit(user_info)

    def _cancel_login_test(self):
        """取消登录测试"""
        # 防止重复触发
        if not hasattr(self, '_login_cancelled'):
            self._login_cancelled = True
            
            if self.worker_thread and self.worker_thread.isRunning():
                self.update_log("用户取消登录测试...", True)
                # 尝试优雅地停止线程
                try:
                    self.worker_thread.terminate()
                    self.worker_thread.wait(3000)  # 等待3秒
                    if self.worker_thread.isRunning():
                        self.worker_thread.kill()  # 强制终止
                except Exception as e:
                    self.update_log(f"停止线程时出错: {e}", True)
                
                if self.progress_dialog:
                    try:
                        self.progress_dialog.canceled.disconnect()
                        self.progress_dialog.close()
                    except:
                        pass
                    self.progress_dialog = None
                
                self.test_login_btn.setEnabled(True)
                self.worker_thread = None

    def refresh_user_info(self):
        """刷新用户信息"""
        if not self.current_user_info:
            QMessageBox.information(self, "提示", "请先测试登录")
            return

        # 重新执行登录测试来刷新用户信息
        self._test_login()

    def _start_export(self):
        """Initiates the data export process in a separate thread."""
        account = self.account_input.text().strip()
        password = self.password_input.text().strip()
        product_name = self.product_name_input.text().strip()
        project_name = self.project_name_input.text().strip()
        assigned_to = self.assigned_combo.currentText().strip()
        test_report_id = self.test_report_id_input.text().strip()
        download_dir = self.download_dir_display.text().strip()
        headless_mode = self.headless_checkbox.isChecked()

        if not account or not password or not product_name or not download_dir or not project_name:
            QMessageBox.warning(self, "输入错误", "账号、密码、产品名称，项目名称和下载目录都不能为空，请填写完整。")
            return

        # 检查下载目录 - 规范化路径以处理编码问题
        normalized_download_dir = os.path.normpath(os.path.abspath(download_dir))
        download_dir = normalized_download_dir

        print(f'---------------',download_dir)
        
        if not os.path.exists(download_dir):
            try:
                os.makedirs(download_dir, exist_ok=True)
                self.update_log(f"已创建下载目录: {download_dir}", False)
            except Exception as e:
                self.update_log(f"错误: 无法创建下载目录 '{download_dir}': {e}", True)
                QMessageBox.critical(self, "目录创建失败", f"无法创建下载目录，请检查权限或路径是否合法。\n错误: {e}")
                return
        elif not os.path.isdir(download_dir):
            self.update_log(f"错误: 下载目录 '{download_dir}' 存在但不是一个目录。", True)
            QMessageBox.critical(self, "路径错误", f"下载目录 '{download_dir}' 存在但不是一个目录，请重新选择。")
            return

        self.save_settings()

        self.log_output.clear()
        self.update_log("--- 开始执行自动化任务 ---", False)
        self.export_button.setEnabled(False)

        # 重置完成标志
        if hasattr(self, '_export_completed'):
            delattr(self, '_export_completed')

        self.progress_dialog = QProgressDialog("导出进度", "取消", 0, 100, self)
        self.progress_dialog.setWindowTitle("导出进度")
        self.progress_dialog.setWindowModality(Qt.WindowModal)
        self.progress_dialog.setAutoClose(True)
        self.progress_dialog.setAutoReset(True)
        self.progress_dialog.setMinimumDuration(0)
        self.progress_dialog.setValue(0)
        self.progress_dialog.setLabelText("正在准备...")
        self.progress_dialog.show()

        # 创建导出工作线程
        self.worker_thread = SeleniumWorker(
            account, password, product_name,project_name, assigned_to, test_report_id, download_dir, headless_mode, "export"
        )
        self.worker_thread.log_signal.connect(self.update_log)
        self.worker_thread.status_signal.connect(self.progress_dialog.setLabelText)
        self.worker_thread.finished_signal.connect(self._export_finished)
        self.worker_thread.progress_signal.connect(self.progress_dialog.setValue)
        self.worker_thread.user_info_signal.connect(self._on_user_info_received)  # 也监听用户信息
        self.progress_dialog.canceled.connect(self._cancel_export)

        self.worker_thread.start()

    def _export_finished(self, success, message):
        """Handles the completion of the export process."""
        # 先断开取消信号连接，避免误触发
        if self.progress_dialog:
            try:
                self.progress_dialog.canceled.disconnect()
            except:
                pass  # 如果信号未连接，忽略异常
        
        # 设置完成标志，避免取消操作被误触发
        self._export_completed = True
        
        self.export_button.setEnabled(True)
        if self.progress_dialog:
            self.progress_dialog.close()
            self.progress_dialog = None

        self.update_log(f"\n--- 任务完成: {'成功' if success else '失败'} ---", False)
        self.update_log(message, not success)
        if success:
            QMessageBox.information(self, "任务完成", message)
        else:
            QMessageBox.critical(self, "任务失败", message)
        
        # 确保线程资源清理
        if self.worker_thread:
            try:
                self.worker_thread.quit()
                self.worker_thread.wait(1000)  # 等待1秒
            except Exception as e:
                self.update_log(f"清理线程资源时出错: {e}", True)
            self.worker_thread = None

    def _cancel_export(self):
        """Handles cancellation of the export process."""
        # 添加更严格的状态检查，避免在任务完成时误触发
        if (self.worker_thread and 
            self.worker_thread.isRunning() and 
            not hasattr(self, '_export_completed')):
            
            self.update_log("用户请求取消任务，正在停止...", True)
            
            # 设置完成标志，避免重复处理
            self._export_completed = True
            
            try:
                # 调用SeleniumWorker的cancel方法
                if hasattr(self.worker_thread, 'cancel'):
                    self.worker_thread.cancel()
                
                # 等待线程自然结束
                self.worker_thread.wait(5000)  # 等待5秒
                
                # 如果线程仍在运行，强制终止
                if self.worker_thread.isRunning():
                    self.worker_thread.terminate()
                    self.worker_thread.wait(2000)  # 再等待2秒
                    if self.worker_thread.isRunning():
                        self.worker_thread.kill()  # 强制终止
                        
            except Exception as e:
                self.update_log(f"停止线程时出错: {e}", True)

            if self.progress_dialog:
                try:
                    self.progress_dialog.canceled.disconnect()
                except:
                    pass
                self.progress_dialog.close()
                self.progress_dialog = None

            self.export_button.setEnabled(True)
            self.worker_thread = None
            QMessageBox.information(self, "任务取消", "导出任务已成功取消。")
        else:
            # 只有在真正没有任务运行时才显示此消息
            if not self.worker_thread or not self.worker_thread.isRunning():
                self.update_log("没有正在运行的任务可以取消。", False)

    def update_log(self, message, is_error=False):
        """Appends a message to the log QTextEdit with a timestamp."""

        # 获取当前日期和时间
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 格式化带有时间戳的消息
        formatted_message = f"[{timestamp}] {message}"

        cursor = self.log_output.textCursor()
        format = QTextCharFormat()
        # 设置文本颜色
        if is_error:
            format.setForeground(QColor("red"))
        else:
            format.setForeground(QColor("black"))
        # 使用 insertText 方法来应用格式
        cursor.movePosition(QTextCursor.End)
        cursor.insertText(formatted_message, format)
        # 插入换行符
        cursor.insertText('\n')
        # 确保光标移动到末尾
        self.log_output.setTextCursor(cursor)

    def save_settings(self):
        """Saves settings specific to this tab."""
        settings = {
            "account": self.account_input.text(),
            "password": self.password_input.text(),
            "product_name": self.product_name_input.text(),
            "project_name":self.project_name_input.text(),
            "test_report_id": self.test_report_id_input.text(),
            "download_dir": self.download_dir_display.text(),
            "headless_mode": self.headless_checkbox.isChecked()
        }
        self.settings_manager.save_settings("zentao_export", settings, self.update_log)

    def load_settings(self):
        """Loads settings specific to this tab."""
        default_settings = {
            "account": "",
            "password": "",
            "product_name": "",
            "project_name": "",
            "test_report_id": TEST_REPORT_ID_DEFAULT,
            "download_dir": DOWNLOAD_DIR,
            "headless_mode": HEADLESS_MODE_DEFAULT
        }
        loaded_settings = self.settings_manager.load_settings(
            "zentao_export",
            default_settings=default_settings,
            log_callback=self.update_log
        )
        self.product_name_input.setText(loaded_settings.get("product_name", ""))
        self.project_name_input.setText(loaded_settings.get("project_name", ""))
        self.test_report_id_input.setText(loaded_settings.get("test_report_id", TEST_REPORT_ID_DEFAULT))
        self.download_dir_display.setText(loaded_settings.get("download_dir", DOWNLOAD_DIR))
        self.headless_checkbox.setChecked(loaded_settings.get("headless_mode", HEADLESS_MODE_DEFAULT))
        self.account_input.setText(loaded_settings.get("account", ""))
        self.password_input.setText(loaded_settings.get("password", ""))

        # 确保默认下载目录存在
        initial_download_dir = self.download_dir_display.text()
        if initial_download_dir and not os.path.exists(initial_download_dir):
            try:
                os.makedirs(initial_download_dir, exist_ok=True)
                self.update_log(f"已创建默认下载目录: {initial_download_dir}", False)
            except Exception as e:
                self.update_log(f"警告: 无法创建默认下载目录 '{initial_download_dir}': {e}", True)
                self.download_dir_display.setText(os.path.expanduser("~"))
