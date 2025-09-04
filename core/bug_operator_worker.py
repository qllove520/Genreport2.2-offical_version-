# core/bug_operator_worker.py - BUG操作工作线程

import os
import sys
import re
import time
import traceback
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException

from PyQt5.QtCore import QThread, pyqtSignal
from config.settings import EDGEDRIVER_PATH, ZEN_TAO_BASE_URL, PROJECT_TABLE_PATH


class BugOperatorWorker(QThread):
    """BUG操作工作线程 - 无头模式"""

    log_signal = pyqtSignal(str, bool)  # message, is_error
    bugs_data_signal = pyqtSignal(list)  # 发送BUG数据列表
    operation_result_signal = pyqtSignal(bool, str)  # 操作结果
    finished_signal = pyqtSignal(bool, str)  # 完成信号

    def __init__(self, manager_account, manager_password, operator_name, operation_type, query_params=None,
                 operation_params=None):
        super().__init__()
        self.manager_account = manager_account
        self.manager_password = manager_password
        self.operator_name = operator_name
        self.operation_type = operation_type  # 'query' or 'execute'
        self.query_params = query_params or {}
        self.operation_params = operation_params or {}
        self.base_url = ZEN_TAO_BASE_URL
        self.driver = None
        self.keep_browser_open = False  # 新增：控制是否保持浏览器打开

    def run(self):
        """主执行逻辑"""
        try:
            self.log_signal.emit("初始化无头浏览器...", False)

            if not self._setup_driver():
                self.finished_signal.emit(False, "浏览器启动失败")
                return

            self.log_signal.emit("浏览器启动成功", False)

            if not self._login():
                self.finished_signal.emit(False, "管理员登录失败")
                return

            self.log_signal.emit("管理员登录成功", False)
            self._log_admin_operation("管理员登录用于BUG操作")

            if self.operation_type == 'query':
                self._execute_query()
            elif self.operation_type == 'execute':
                self._execute_operation()
            else:
                self.finished_signal.emit(False, f"未知操作类型: {self.operation_type}")

        except Exception as e:
            self.log_signal.emit(f"BUG操作异常: {e}", True)
            self.log_signal.emit(traceback.format_exc(), True)
            self.finished_signal.emit(False, f"操作异常: {e}")
        finally:
            # 只有在不保持浏览器打开时才清理资源
            if not self.keep_browser_open:
                self._cleanup()

    def _setup_driver(self):
        """设置浏览器驱动 - 支持有头和无头模式"""
        try:
            edge_options = EdgeOptions()
            # 根据操作类型决定是否使用无头模式
            # 查询操作使用无头模式但保持打开，操作执行使用有头模式但初始隐藏
            if self.operation_type == 'query':
                # 查询操作使用无头模式，但保持浏览器在后台运行
                edge_options.add_argument("--headless")
                self.keep_browser_open = True
                self.log_signal.emit("查询模式：浏览器将以无头模式在后台运行，查询完成后保持打开等待后续操作", False)
            else:
                # 操作执行使用有头模式，但初始隐藏浏览器窗口
                self.keep_browser_open = True
                self.show_browser_after_load = True  # 新增：页面加载完成后才显示浏览器
                self.log_signal.emit("操作模式：浏览器初始隐藏，页面加载完成后才显示", False)
            
            # Edge浏览器特定的配置
            edge_options.add_argument("--disable-web-security")
            edge_options.add_argument("--disable-features=VizDisplayCompositor")
            edge_options.add_argument("--disable-dev-shm-usage")
            edge_options.add_argument("--no-sandbox")
            edge_options.add_argument("--disable-gpu")
            edge_options.add_argument("--disable-extensions")
            edge_options.add_argument("--disable-plugins")
            edge_options.add_argument("--disable-background-timer-throttling")
            edge_options.add_argument("--disable-backgrounding-occluded-windows")
            edge_options.add_argument("--disable-renderer-backgrounding")
            edge_options.add_argument("--disable-features=TranslateUI")
            edge_options.add_argument("--disable-ipc-flooding-protection")
            
            # 设置窗口大小
            edge_options.add_argument("--window-size=1920,1080")
            # 移除 --start-maximized 参数，改用JavaScript控制
            
            # 如果是操作模式且需要页面加载后显示，则初始隐藏窗口
            if hasattr(self, 'show_browser_after_load') and self.show_browser_after_load:
                edge_options.add_argument("--window-position=-9999,-9999")  # 将窗口移到屏幕外
            
            # 设置用户代理
            edge_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0")

            if EDGEDRIVER_PATH and os.path.exists(EDGEDRIVER_PATH):
                service = EdgeService(executable_path=EDGEDRIVER_PATH)
                self.driver = webdriver.Edge(service=service, options=edge_options)
            else:
                self.driver = webdriver.Edge(options=edge_options)

            # 隐藏自动化标识
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

            self.driver.set_page_load_timeout(60)
            self.driver.implicitly_wait(10)
            
            # 根据模式设置窗口显示
            try:
                if hasattr(self, 'show_browser_after_load') and self.show_browser_after_load:
                    # 操作模式：初始隐藏窗口，等待页面加载完成后显示
                    self.log_signal.emit("浏览器窗口初始隐藏，等待页面加载完成后显示", False)
                else:
                    # 查询模式：正常显示窗口
                    # 使用Edge原生的最大化方法
                    self.driver.maximize_window()
                    
                    # 获取屏幕尺寸
                    screen_width = self.driver.execute_script("return window.screen.availWidth;")
                    screen_height = self.driver.execute_script("return window.screen.availHeight;")
                    
                    # 获取窗口尺寸
                    window_width = self.driver.execute_script("return window.outerWidth;")
                    window_height = self.driver.execute_script("return window.outerHeight;")
                    
                    # 计算居中位置
                    x = (screen_width - window_width) // 2
                    y = (screen_height - window_height) // 2
                    
                    # 移动窗口到屏幕中央
                    self.driver.set_window_position(x, y)
                    self.log_signal.emit("浏览器窗口已最大化并居中显示。", False)
            except Exception as e:
                self.log_signal.emit(f"窗口设置失败: {e}", False)
            
            return True

        except Exception as e:
            self.log_signal.emit(f"浏览器初始化失败: {e}", True)
            return False

    def _login(self):
        """登录禅道"""
        try:
            self.driver.get(f"{self.base_url}/user-login.html")

            # 等待登录页面加载
            wait = WebDriverWait(self.driver, 15)
            account_input = wait.until(EC.element_to_be_clickable((By.ID, 'account')))
            password_input = wait.until(EC.element_to_be_clickable((By.NAME, 'password')))

            # 输入账号密码
            account_input.clear()
            account_input.send_keys(self.manager_account)

            password_input.clear()
            password_input.send_keys(self.manager_password)

            # 点击登录
            login_button = wait.until(EC.element_to_be_clickable((By.ID, 'submit')))
            login_button.click()

            # 等待登录完成
            wait.until(
                EC.any_of(
                    EC.url_changes(f"{self.base_url}/user-login.html"),
                    EC.presence_of_element_located((By.CSS_SELECTOR, '.main-header'))
                )
            )

            # 检查登录结果
            if "登录失败" in self.driver.page_source or "user-login" in self.driver.current_url:
                return False

            return True

        except Exception as e:
            self.log_signal.emit(f"登录异常: {e}", True)
            return False

    def _execute_query(self):
        """执行BUG查询"""
        try:
            project_name = self.query_params.get('project_name', '')

            # 查找项目ID
            print(f'---------------debug-111111111111----------{project_name}')
            project_id = self._find_project_id(project_name)
            if not project_id:
                self.finished_signal.emit(False, f"未找到项目: {project_name}")
                return

            self.log_signal.emit(f"找到项目ID: {project_id}", False)

            # 导航到BUG页面
            #project-bug-2242-status,id_desc-0-all.html
            bug_url = f"{self.base_url}/project-bug-{project_id}-resolution_asc-0-all-0--2000-1.html"
            self.driver.get(bug_url)

            # 等待页面加载
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.TAG_NAME, 'body'))
            )
            # 应用查询条件
            self._apply_query_filters()

            # 解析BUG列表
            bugs_data = self._parse_bug_list()
            print(f'bugs_data:{bugs_data}')

            if bugs_data:
                self.bugs_data_signal.emit(bugs_data)
                self.finished_signal.emit(True, f"查询完成，找到 {len(bugs_data)} 个BUG。浏览器保持打开状态，您可以进行导出或操作。")
            else:
                self.finished_signal.emit(False, "未查询到任何BUG数据")

        except Exception as e:
            self.log_signal.emit(f"查询BUG失败: {e}", True)
            self.finished_signal.emit(False, f"查询失败: {e}")

    def _execute_operation(self):
        """执行BUG操作"""
        try:
            bug_id = self.operation_params.get('bug_id')
            action = self.operation_params.get('action')
            comment = self.operation_params.get('comment')

            self.log_signal.emit(f"正在执行操作: {action} - BUG ID: {bug_id}", False)

            # 导航到BUG详情页
            #http://10.200.10.220/zentao/bug-view-37188.html
            bug_detail_url = f"{self.base_url}/bug-view-{bug_id}.html"
            self.driver.get(bug_detail_url)

            # 等待页面加载
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, 'body'))
            )

            # 页面加载完成，现在显示浏览器并设置操作限制
            self._show_browser_and_set_restrictions()
            
            # 调试：检查页面内容
            self._debug_page_content()

            # 根据操作类型执行相应操作
            success = False
            if action == "关闭BUG":
                success = self._close_bug(bug_id, comment)
            elif action == "激活BUG":
                success = self._activate_bug(bug_id, comment)
            elif action == "解决BUG":
                success = self._resolve_bug(bug_id, comment)
            elif action == "指派BUG":
                success = self._assign_bug(bug_id, comment)
            else:
                self.operation_result_signal.emit(False, f"不支持的操作类型: {action}")
                return

            if success:
                self._log_admin_operation(f"BUG操作: {action} - BUG ID: {bug_id}")
                self.operation_result_signal.emit(True, f"BUG {bug_id} {action}操作成功")
                self.finished_signal.emit(True, f"操作成功完成")
            else:
                self.operation_result_signal.emit(False, f"BUG {bug_id} {action}操作失败")
                self.finished_signal.emit(False, f"操作失败")

        except Exception as e:
            self.log_signal.emit(f"执行BUG操作失败: {e}", True)
            self.operation_result_signal.emit(False, f"操作异常: {e}")
            self.finished_signal.emit(False, f"操作异常: {e}")

    def _find_project_id(self, project_name):
        """查找项目ID"""
        try:
            # 导航到项目列表页面 - 更新路径到reference目录
            project_table_path = PROJECT_TABLE_PATH

            # 检查文件
            if not os.path.exists(project_table_path):
                self.log_signal.emit(f"项目表文件不存在: {project_table_path}", True)
                return None

            file_size = os.path.getsize(project_table_path)
            timeout = max(30, file_size / 1024 / 1024 * 10)
            self.log_signal.emit(f"项目表文件大小: {file_size / 1024 / 1024:.2f}MB，超时时间: {timeout:.1f}秒", False)

            project_table_url = f"file:///{project_table_path.replace(os.sep, '/')}"
            self.driver.get(project_table_url)

            # 等待页面加载
            WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'a[href*="project-view"]'))
            )

            # 等待页面完全渲染
            WebDriverWait(self.driver, 10).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )

            # 查找所有匹配关键字的 <tr>
            print(f"project_name:{project_name}")
            matching_trs = self.driver.find_elements(
                By.XPATH, f"//tr[.//*[contains(text(), '{project_name}') or contains(@title, '{project_name}')]]"
            )
            print('matching_trs', matching_trs)

            if not matching_trs:
                self.log_signal.emit(f"未找到匹配项目: {project_name}", True)
                return None

            for tr in matching_trs:
                try:
                    href = tr.find_element(By.XPATH, ".//a[contains(@href, 'project-view-')]").get_attribute("href")
                    project_id = re.search(r"project-view-(\d+)", href).group(1)
                    self.log_signal.emit(f"找到项目ID: {project_id}", False)
                    return project_id
                except Exception as e:
                    self.log_signal.emit(f"解析项目ID失败: {e}", True)
                    continue

            return None

        except Exception as e:
            self.log_signal.emit(f"查找项目ID失败: {e}", True)
            return None

    def _apply_query_filters(self):
        """应用查询过滤条件"""
        try:
            # 这里可以根据assigned_to和solution参数设置过滤条件
            # 由于禅道的界面可能有所不同，需要根据实际情况调整选择器
            assigned_to = self.query_params.get('assigned_to', 'all')
            if assigned_to != 'all':
                # 尝试找到状态过滤器并设置
                try:
                    assigned_to_select = self.driver.find_element(By.NAME, 'assigned_to')
                    Select(assigned_to_select).select_by_value(assigned_to)
                    self.log_signal.emit(f"已设置分配过滤: {assigned_to}", False)
                except:
                    pass

            solution = self.query_params.get('solution', 'all')
            if solution != 'all':
                # 尝试找到严重程度过滤器并设置
                try:
                    solution_select = self.driver.find_element(By.NAME, 'solution')
                    Select(solution_select).select_by_value(solution)
                    self.log_signal.emit(f"已设置解决方案过滤: {solution}", False)
                except:
                    pass

        except Exception as e:
            self.log_signal.emit(f"应用查询过滤器失败: {e}", True)

    def _parse_bug_list(self):
        """解析BUG列表"""
        print(self.driver.page_source)
        try:
            bugs_data = []
            # 查找BUG列表表格
            table_selectors = [
                'table.table',
                '#bugList table',
                'main-table',
                'table'
            ]

            table = None
            for selector in table_selectors:
                try:
                    table = self.driver.find_element(By.CSS_SELECTOR, selector)
                    print('table:', table)
                    if table:
                        break
                except:
                    continue

            if not table:
                self.log_signal.emit("未找到BUG列表表格", True)
                return bugs_data

            # 解析表格行
            rows = table.find_elements(By.TAG_NAME, 'tr')[1:]  # 跳过标题行
            print(f"表格行数(不含标题): {len(rows)}")

            # 预先获取过滤参数，避免在循环中重复获取
            assigned_to_filter = self.query_params.get('assigned_to', '全部')
            solution_filter = self.query_params.get('solution', '全部')
            bug_id_filter = self.query_params.get('bug_id', '')

            is_method1 = bool(assigned_to_filter not in ('all', '') and solution_filter not in ('all', ''))
            is_method2 = bool(bug_id_filter)

            for row in rows:
                cells = row.find_elements(By.TAG_NAME, 'td')
                print(f"行单元格数: {len(cells)}")
                print(f'----1111111111111111111111111111111--------------')
                if len(cells) >= 6:  # 确保有足够的列
                    try:
                        bug_info = {
                            'id': self._extract_bug_id(cells[0]),
                            'title': cells[3].text.strip() if len(cells) > 1 else '',
                            'status': cells[1].text.strip() if len(cells) > 2 else '',
                            'opened_by': cells[4].text.strip() if len(cells) > 4 else '',
                            'assigned_to': cells[5].text.strip() if len(cells) > 5 else '',
                            'solution': cells[7].text.strip() if len(cells) > 6 else ''
                        }
                        print('----------------------222222222222222222222222-------------------------')
                        print(cells[0].text.strip(), cells[1].text.strip(), cells[2].text.strip(),
                              cells[3].text.strip(), cells[4].text.strip(), cells[5].text.strip(),
                              cells[6].text.strip(), cells[7].text.strip(), cells[8].text.strip())

                        # 仅当有有效ID时进行处理
                        if bug_info['id']:
                            print('------2222222----',is_method1,is_method2)
                            if is_method1:
                                print('----333333------',bug_info['assigned_to'],bug_info['solution'])
                                print('----44444444------', type(bug_info['assigned_to']), type(bug_info['solution']))
                                # 修正：直接使用 bug_info 字典中的值进行判断
                                if assigned_to_filter == '全部' and solution_filter == '全部':
                                    bugs_data.append(bug_info)
                                elif bug_info['assigned_to'] == assigned_to_filter and bug_info['solution'] == solution_filter:
                                    print('-----5555555555-------')
                                    bugs_data.append(bug_info)
                            elif is_method2:
                                # 修正：直接使用 bug_info 字典中的值进行判断
                                if  str(bug_info['id']) == bug_id_filter:
                                    bugs_data.append(bug_info)
                            else:
                                # 默认情况下，如果没有特定的过滤方式，则全部添加
                                bugs_data.append(bug_info)
                    except Exception as e:
                        self.log_signal.emit(f"解析BUG行失败: {e}", True)
                        continue

            return bugs_data

        except Exception as e:
            self.log_signal.emit(f"解析BUG列表失败: {e}", True)
            return []

    def _extract_bug_id(self, cell):
        """从单元格中提取BUG ID"""
        try:
            # 尝试从链接中提取ID
            link = cell.find_element(By.TAG_NAME, 'a')
            href = link.get_attribute('href')
            print(f"提取BUG ID，链接: {href}")
            if href:
                # 从URL中提取ID
                parts = href.split('-')
                for part in parts:
                    if part.isdigit():
                        return part

            # 如果没有链接，直接取文本
            text = cell.text.strip()
            if text.isdigit():
                return text

        except:
            # 如果提取失败，返回单元格文本
            text = cell.text.strip()
            # 提取数字部分
            import re
            numbers = re.findall(r'\d+', text)
            if numbers:
                return numbers[0]

        return ""

    def _close_bug(self, bug_id, comment):
        """关闭BUG"""
        try:
            # 查找关闭按钮
            close_button_selectors = [
                'a[href*="bug-close"]',
                '.btn:contains("关闭")',
                'button:contains("关闭")'
            ]

            close_button = None
            for selector in close_button_selectors:
                try:
                    if ':contains(' in selector:
                        # 使用XPath查找包含文本的元素
                        xpath = f"//a[contains(text(),'关闭')] | //button[contains(text(),'关闭')]"
                        close_button = self.driver.find_element(By.XPATH, xpath)
                    else:
                        close_button = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if close_button:
                        break
                except:
                    continue

            if not close_button:
                self.log_signal.emit("未找到关闭按钮", True)
                return False

            close_button.click()

            # 等待关闭页面加载
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, 'form'))
            )

            # 填写备注
            return self._fill_comment_and_submit(comment)

        except Exception as e:
            self.log_signal.emit(f"关闭BUG失败: {e}", True)
            return False

    def _activate_bug(self, bug_id, comment):
        """激活BUG"""
        try:
            # 查找激活按钮
            activate_button_selectors = [
                'a[href*="bug-activate"]',
                '.btn:contains("激活")',
                'button:contains("激活")'
            ]

            activate_button = None
            for selector in activate_button_selectors:
                try:
                    if ':contains(' in selector:
                        xpath = f"//a[contains(text(),'激活')] | //button[contains(text(),'激活')]"
                        activate_button = self.driver.find_element(By.XPATH, xpath)
                    else:
                        activate_button = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if activate_button:
                        break
                except:
                    continue

            if not activate_button:
                self.log_signal.emit("未找到激活按钮", True)
                return False

            activate_button.click()

            # 等待激活页面加载
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, 'form'))
            )

            # 填写备注
            return self._fill_comment_and_submit(comment)

        except Exception as e:
            self.log_signal.emit(f"激活BUG失败: {e}", True)
            return False

    def _resolve_bug(self, bug_id, comment):
        """解决BUG"""
        try:
            # 查找解决按钮
            resolve_button_selectors = [
                'a[href*="bug-resolve"]',
                '.btn:contains("解决")',
                'button:contains("解决")'
            ]

            resolve_button = None
            for selector in resolve_button_selectors:
                try:
                    if ':contains(' in selector:
                        xpath = f"//a[contains(text(),'解决')] | //button[contains(text(),'解决')]"
                        resolve_button = self.driver.find_element(By.XPATH, xpath)
                    else:
                        resolve_button = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if resolve_button:
                        break
                except:
                    continue

            if not resolve_button:
                self.log_signal.emit("未找到解决按钮", True)
                return False

            resolve_button.click()

            # 等待解决页面加载
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, 'form'))
            )

            # 填写备注
            return self._fill_comment_and_submit(comment)

        except Exception as e:
            self.log_signal.emit(f"解决BUG失败: {e}", True)
            return False

    def _assign_bug(self, bug_id, comment):
        """指派BUG"""
        try:
            # 查找指派按钮
            assign_button_selectors = [
                'a[href*="bug-assignTo"]',
                '.btn:contains("指派")',
                'button:contains("指派")'
            ]

            assign_button = None
            for selector in assign_button_selectors:
                try:
                    if ':contains(' in selector:
                        xpath = f"//a[contains(text(),'指派')] | //button[contains(text(),'指派')]"
                        assign_button = self.driver.find_element(By.XPATH, xpath)
                    else:
                        assign_button = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if assign_button:
                        break
                except:
                    continue

            if not assign_button:
                self.log_signal.emit("未找到指派按钮", True)
                return False

            assign_button.click()

            # 等待指派页面加载
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, 'form'))
            )

            # 填写备注
            return self._fill_comment_and_submit(comment)

        except Exception as e:
            self.log_signal.emit(f"指派BUG失败: {e}", True)
            return False

    def _fill_comment_and_submit(self, comment):
        """填写备注并提交"""
        try:
            # 查找备注输入框
            comment_selectors = [
                'textarea[name="comment"]',
                'textarea[name="remark"]',
                'textarea[name="note"]',
                '#comment',
                '#remark',
                '#note'
            ]

            comment_field = None
            for selector in comment_selectors:
                try:
                    comment_field = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if comment_field:
                        break
                except:
                    continue

            if comment_field:
                comment_field.clear()
                comment_field.send_keys(comment)
                self.log_signal.emit("已填写操作备注", False)
            else:
                self.log_signal.emit("未找到备注输入框", True)

            # 查找并点击提交按钮
            submit_selectors = [
                'button[type="submit"]',
                'input[type="submit"]',
                '.btn-primary',
                '.btn-success',
                'button:contains("提交")',
                'button:contains("保存")'
            ]

            submit_button = None
            for selector in submit_selectors:
                try:
                    if ':contains(' in selector:
                        xpath = f"//button[contains(text(),'提交')] | //button[contains(text(),'保存')] | //input[@value='提交'] | //input[@value='保存']"
                        submit_button = self.driver.find_element(By.XPATH, xpath)
                    else:
                        submit_button = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if submit_button:
                        break
                except:
                    continue

            if not submit_button:
                self.log_signal.emit("未找到提交按钮", True)
                return False

            submit_button.click()

            # 等待提交完成
            # 优化：减少等待时间
            time.sleep(1)  # 从2秒减少到1秒

            # 检查是否提交成功（可以根据页面变化或成功消息判断）
            if "成功" in self.driver.page_source or "success" in self.driver.current_url.lower():
                self.log_signal.emit("操作提交成功", False)
                return True
            else:
                self.log_signal.emit("操作可能未成功提交", True)
                return True  # 假设成功，因为没有明确的失败标识

        except Exception as e:
            self.log_signal.emit(f"填写备注并提交失败: {e}", True)
            return False

    def _log_admin_operation(self, operation_type):
        """记录管理员操作日志"""
        try:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            log_content = f"[{timestamp}] 管理员账号 {self.manager_account} 被操作人 {self.operator_name} 用于 {operation_type}\n"

            # 创建日志目录
            log_dir = os.path.join(os.getcwd(), "logs")
            if not os.path.exists(log_dir):
                os.makedirs(log_dir)

            # 写入操作日志
            log_file = os.path.join(log_dir, "admin_operations.log")
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(log_content)

            self.log_signal.emit(f"管理员操作已记录: {operation_type}", False)

        except Exception as e:
            self.log_signal.emit(f"记录管理员操作失败: {e}", True)

    def _cleanup(self):
        """清理资源"""
        if self.driver:
            try:
                self.driver.quit()
                self.log_signal.emit("浏览器已关闭", False)
            except:
                pass
            finally:
                self.driver = None

    def close_browser(self):
        """手动关闭浏览器"""
        if self.driver:
            try:
                self.driver.quit()
                self.log_signal.emit("浏览器已手动关闭", False)
            except:
                pass
            finally:
                self.driver = None
            self.keep_browser_open = False

    def _highlight_operation_area(self):
        """突出显示BUG详情页面的操作区域并限制操作权限"""
        try:
            # 1. 隐藏Bug详细和操作区域（顶部导航栏中的管理员信息）
            self._hide_admin_area()
            
            # 2. 突出显示2号区域（底部操作按钮区域）
            self._highlight_action_buttons()
            
            # 3. 禁用其他区域的交互
            self._disable_other_interactions()
            
            # 4. 添加操作提示
            self._add_operation_tips()
            
            self.log_signal.emit("✅ 红色框框区域已设置，只允许操作底部按钮区域", False)
            
        except Exception as e:
            self.log_signal.emit(f"设置操作区域失败: {e}", True)

    def _hide_admin_area(self):
        """隐藏Bug详细和操作区域（管理员信息区域）"""
        try:
            # 定义需要隐藏的管理员相关元素选择器
            admin_selectors = [
                # 顶部导航栏中的管理员信息
                '.navbar .user-info',
                '.navbar .admin-info',
                '.navbar .user-dropdown',
                '.navbar .logout-link',
                '.navbar a[href*="logout"]',
                '.navbar a[href*="admin"]',
                # 用户信息显示区域
                '.user-panel',
                '.admin-panel',
                # 具体的admin和退出链接
                'a:contains("admin")',
                'a:contains("退出")',
                'a:contains("logout")'
            ]
            
            # 尝试隐藏管理员相关元素
            hidden_count = 0
            for selector in admin_selectors:
                try:
                    if ':contains(' in selector:
                        # 使用XPath查找包含特定文本的元素
                        text = selector.split('"')[1]
                        xpath = f"//a[contains(text(), '{text}')] | //span[contains(text(), '{text}')] | //div[contains(text(), '{text}')]"
                        elements = self.driver.find_elements(By.XPATH, xpath)
                    else:
                        elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    
                    for element in elements:
                        # 隐藏元素
                        self.driver.execute_script("""
                            arguments[0].style.display = 'none';
                            arguments[0].style.visibility = 'hidden';
                            arguments[0].style.opacity = '0';
                            arguments[0].style.pointerEvents = 'none';
                        """, element)
                        hidden_count += 1
                        
                except Exception as e:
                    continue
            
            self.log_signal.emit(f"已隐藏 {hidden_count} 个管理员相关元素", False)
            
        except Exception as e:
            self.log_signal.emit(f"隐藏管理员区域失败: {e}", True)

    def _highlight_action_buttons(self):
        """突出显示2号区域（底部操作按钮）"""
        try:
            # 定义底部操作按钮区域的选择器
            action_button_selectors = [
                # 底部操作栏
                '.action-panel',
                '.button-panel',
                '.operation-panel',
                '.main-actions',
                '.bug-actions',
                # 具体的按钮区域
                '.main-table .actions',
                '.detail-panel .actions',
                # 按钮容器
                '.btn-group',
                '.action-buttons',
                '.operation-buttons'
            ]
            
            # 尝试找到并突出显示操作按钮区域
            highlighted = False
            for selector in action_button_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        for element in elements:
                            # 添加红色边框和背景高亮
                            self.driver.execute_script("""
                                arguments[0].style.border = '3px solid #ff0000';
                                arguments[0].style.backgroundColor = '#fff5f5';
                                arguments[0].style.boxShadow = '0 0 10px rgba(255, 0, 0, 0.3)';
                                arguments[0].style.position = 'relative';
                                arguments[0].style.zIndex = '9999';
                                arguments[0].style.padding = '10px';
                                arguments[0].style.margin = '5px';
                            """, element)
                            highlighted = True
                            self.log_signal.emit(f"已突出显示操作按钮区域: {selector}", False)
                except Exception as e:
                    continue
            
            if not highlighted:
                # 如果没有找到特定的按钮区域，尝试突出显示所有按钮
                buttons = self.driver.find_elements(By.CSS_SELECTOR, 'button, .btn, input[type="button"], input[type="submit"]')
                if buttons:
                    for button in buttons:
                        self.driver.execute_script("""
                            arguments[0].style.border = '2px solid #ff0000';
                            arguments[0].style.backgroundColor = '#fff5f5';
                            arguments[0].style.boxShadow = '0 0 5px rgba(255, 0, 0, 0.3)';
                        """, button)
                    self.log_signal.emit(f"已突出显示 {len(buttons)} 个操作按钮", False)
            
        except Exception as e:
            self.log_signal.emit(f"突出显示操作按钮失败: {e}", True)

    def _disable_other_interactions(self):
        """禁用其他区域的交互"""
        try:
            # 禁用除操作按钮外的其他交互元素
            self.driver.execute_script("""
                // 禁用所有链接（除了操作按钮区域内的）
                var links = document.querySelectorAll('a:not(.action-panel a):not(.button-panel a):not(.operation-panel a)');
                for (var i = 0; i < links.length; i++) {
                    links[i].style.pointerEvents = 'none';
                    links[i].style.opacity = '0.5';
                    links[i].style.cursor = 'not-allowed';
                }
                
                // 禁用所有输入框（除了操作按钮区域内的）
                var inputs = document.querySelectorAll('input:not(.action-panel input):not(.button-panel input):not(.operation-panel input)');
                for (var i = 0; i < inputs.length; i++) {
                    inputs[i].disabled = true;
                    inputs[i].style.opacity = '0.5';
                }
                
                // 禁用所有下拉框（除了操作按钮区域内的）
                var selects = document.querySelectorAll('select:not(.action-panel select):not(.button-panel select):not(.operation-panel select)');
                for (var i = 0; i < selects.length; i++) {
                    selects[i].disabled = true;
                    selects[i].style.opacity = '0.5';
                }
                
                // 禁用所有其他按钮（除了操作按钮区域内的）
                var buttons = document.querySelectorAll('button:not(.action-panel button):not(.button-panel button):not(.operation-panel button)');
                for (var i = 0; i < buttons.length; i++) {
                    buttons[i].disabled = true;
                    buttons[i].style.opacity = '0.5';
                    buttons[i].style.cursor = 'not-allowed';
                }
            """)
            
            self.log_signal.emit("已禁用其他区域的交互功能", False)
            
        except Exception as e:
            self.log_signal.emit(f"禁用其他交互失败: {e}", True)

    def _show_browser_and_set_restrictions(self):
        """页面加载完成后设置严格限制并显示浏览器"""
        try:
            # 1. 设置严格的操作限制
            self._set_strict_operation_restrictions()
            
            # 2. 隐藏除Bug详细和操作区域外的所有区域
            self._hide_all_except_region1()
            
            # 3. 突出显示Bug详细和操作操作区域
            self._highlight_operation_area()
            
            # 4. 只有在所有限制设置完成后才显示浏览器窗口
            if hasattr(self, 'show_browser_after_load') and self.show_browser_after_load:
                self._show_browser_window()
            
            self.log_signal.emit("✅ 严格操作限制模式已生效，浏览器已显示", False)
            
        except Exception as e:
            self.log_signal.emit(f"设置严格操作限制失败: {e}", True)

    def _show_browser_window(self):
        """显示浏览器窗口"""
        try:
            # 将窗口移动到屏幕中央并最大化
            self.driver.maximize_window()
            
            # 获取屏幕尺寸
            screen_width = self.driver.execute_script("return window.screen.availWidth;")
            screen_height = self.driver.execute_script("return window.screen.availHeight;")
            
            # 获取窗口尺寸
            window_width = self.driver.execute_script("return window.outerWidth;")
            window_height = self.driver.execute_script("return window.outerHeight;")
            
            # 计算居中位置
            x = (screen_width - window_width) // 2
            y = (screen_height - window_height) // 2
            
            # 移动窗口到屏幕中央
            self.driver.set_window_position(x, y)
            
            self.log_signal.emit("浏览器窗口已显示并居中", False)
            
        except Exception as e:
            self.log_signal.emit(f"显示浏览器窗口失败: {e}", True)

    def _set_strict_operation_restrictions(self):
        """设置严格的操作限制"""
        try:
            # 禁用浏览器导航功能
            self.driver.execute_script("""
                // 禁用浏览器前进后退
                window.history.pushState(null, null, window.location.href);
                window.addEventListener('popstate', function() {
                    window.history.pushState(null, null, window.location.href);
                });
                
                // 禁用右键菜单
                document.addEventListener('contextmenu', function(e) {
                    e.preventDefault();
                    return false;
                });
                
                // 禁用键盘快捷键
                document.addEventListener('keydown', function(e) {
                    // 禁用F5刷新
                    if (e.keyCode === 116) {
                        e.preventDefault();
                        return false;
                    }
                    // 禁用Ctrl+R刷新
                    if (e.ctrlKey && e.keyCode === 82) {
                        e.preventDefault();
                        return false;
                    }
                    // 禁用Ctrl+L地址栏
                    if (e.ctrlKey && e.keyCode === 76) {
                        e.preventDefault();
                        return false;
                    }
                    // 禁用F12开发者工具
                    if (e.keyCode === 123) {
                        e.preventDefault();
                        return false;
                    }
                    // 禁用Tab键切换
                    if (e.keyCode === 9) {
                        e.preventDefault();
                        return false;
                    }
                    // 禁用Esc键
                    if (e.keyCode === 27) {
                        e.preventDefault();
                        return false;
                    }
                });
                
                // 禁用地址栏输入
                window.addEventListener('beforeunload', function(e) {
                    e.preventDefault();
                    e.returnValue = '';
                    return '';
                });
                
                // 禁用所有链接点击（除了Bug详细和操作区域的按钮）
                document.addEventListener('click', function(e) {
                    // 检查是否在Bug详细和操作区域的操作按钮内
                    var isInActionArea = false;
                    var target = e.target;
                    
                    // 向上查找父元素，检查是否在操作按钮区域内
                    while (target && target !== document.body) {
                        if (target.classList.contains('action-panel') || 
                            target.classList.contains('button-panel') || 
                            target.classList.contains('operation-panel') || 
                            target.classList.contains('main-actions') || 
                            target.classList.contains('bug-actions') ||
                            target.classList.contains('btn-group') ||
                            target.classList.contains('action-buttons') ||
                            target.classList.contains('operation-buttons') ||
                            target.tagName === 'BUTTON' ||
                            target.type === 'button' ||
                            target.type === 'submit') {
                            isInActionArea = true;
                            break;
                        }
                        target = target.parentElement;
                    }
                    
                    // 如果不在操作按钮区域内，阻止点击
                    if (!isInActionArea) {
                        e.preventDefault();
                        e.stopPropagation();
                        return false;
                    }
                }, true);
                
                // 禁用所有输入框（除了Bug详细和操作区域的输入框）
                document.addEventListener('input', function(e) {
                    var target = e.target;
                    var isInActionArea = false;
                    
                    // 向上查找父元素，检查是否在操作按钮区域内
                    while (target && target !== document.body) {
                        if (target.classList.contains('action-panel') || 
                            target.classList.contains('button-panel') || 
                            target.classList.contains('operation-panel') || 
                            target.classList.contains('main-actions') || 
                            target.classList.contains('bug-actions') ||
                            target.classList.contains('btn-group') ||
                            target.classList.contains('action-buttons') ||
                            target.classList.contains('operation-buttons')) {
                            isInActionArea = true;
                            break;
                        }
                        target = target.parentElement;
                    }
                    
                    // 如果不在操作按钮区域内，阻止输入
                    if (!isInActionArea) {
                        e.preventDefault();
                        e.stopPropagation();
                        return false;
                    }
                }, true);
            """)
            
            # 隐藏地址栏和导航栏（通过CSS）
            self.driver.execute_script("""
                // 尝试隐藏地址栏相关元素
                var addressBarSelectors = [
                    '#address-bar',
                    '.address-bar',
                    '.url-bar',
                    '.navigation-bar',
                    '.browser-toolbar'
                ];
                
                for (var i = 0; i < addressBarSelectors.length; i++) {
                    var elements = document.querySelectorAll(addressBarSelectors[i]);
                    for (var j = 0; j < elements.length; j++) {
                        elements[j].style.display = 'none';
                    }
                }
            """)
            
            self.log_signal.emit("已禁用浏览器导航功能和所有非Bug详细和操作区域操作", False)
            
        except Exception as e:
            self.log_signal.emit(f"设置严格操作限制失败: {e}", True)

    def _hide_all_except_region1(self):
        """只显示重现步骤区域和底部操作按钮"""
        try:
            # 隐藏所有元素，然后只显示重现步骤区域
            self.driver.execute_script("""
                // 首先隐藏所有元素
                var allElements = document.querySelectorAll('*');
                for (var i = 0; i < allElements.length; i++) {
                    var element = allElements[i];
                    if (element.tagName !== 'BODY' && element.tagName !== 'HTML') {
                        element.style.display = 'none';
                        element.style.visibility = 'hidden';
                        element.style.opacity = '0';
                        element.style.pointerEvents = 'none';
                    }
                }
                
                // 设置页面背景为白色
                document.body.style.backgroundColor = '#ffffff';
                document.body.style.overflow = 'hidden';
                
                // 查找并显示重现步骤区域
                var stepsElements = [];
                
                // 方法1：通过文本内容查找
                var allTextElements = document.querySelectorAll('*');
                for (var j = 0; j < allTextElements.length; j++) {
                    var textElement = allTextElements[j];
                    if (textElement.textContent && textElement.textContent.includes('重现步骤')) {
                        // 找到包含"重现步骤"的元素，显示它和它的父容器
                        var parent = textElement.parentElement;
                        while (parent && parent !== document.body) {
                            stepsElements.push(parent);
                            parent = parent.parentElement;
                        }
                        stepsElements.push(textElement);
                        break;
                    }
                }
                
                // 方法2：通过常见的类名查找
                var commonSelectors = [
                    '.bug-steps',
                    '.reproduction-steps',
                    '.steps',
                    '.bug-description',
                    '.bug-content',
                    '.main-content',
                    '.detail-content',
                    '.content'
                ];
                
                for (var k = 0; k < commonSelectors.length; k++) {
                    var elements = document.querySelectorAll(commonSelectors[k]);
                    for (var l = 0; l < elements.length; l++) {
                        if (elements[l].textContent && elements[l].textContent.includes('重现步骤')) {
                            stepsElements.push(elements[l]);
                        }
                    }
                }
                
                // 显示重现步骤区域
                for (var m = 0; m < stepsElements.length; m++) {
                    var stepElement = stepsElements[m];
                    stepElement.style.display = 'block';
                    stepElement.style.visibility = 'visible';
                    stepElement.style.opacity = '1';
                    stepElement.style.pointerEvents = 'auto';
                    stepElement.style.position = 'relative';
                    stepElement.style.zIndex = '9999';
                    stepElement.style.backgroundColor = '#ffffff';
                    stepElement.style.padding = '20px';
                    stepElement.style.margin = '20px';
                    stepElement.style.border = '2px solid #ff0000';
                    stepElement.style.borderRadius = '10px';
                    stepElement.style.width = 'calc(100% - 40px)';
                    stepElement.style.minHeight = '60vh';
                    stepElement.style.overflow = 'visible';
                }
                
                // 查找并显示底部操作按钮
                var buttonSelectors = [
                    '.action-panel',
                    '.button-panel',
                    '.operation-panel',
                    '.main-actions',
                    '.bug-actions',
                    '.btn-group',
                    '.action-buttons',
                    '.operation-buttons',
                    'button',
                    '.btn',
                    'input[type="button"]',
                    'input[type="submit"]'
                ];
                
                for (var n = 0; n < buttonSelectors.length; n++) {
                    var buttonElements = document.querySelectorAll(buttonSelectors[n]);
                    for (var o = 0; o < buttonElements.length; o++) {
                        var buttonElement = buttonElements[o];
                        buttonElement.style.display = 'block';
                        buttonElement.style.visibility = 'visible';
                        buttonElement.style.opacity = '1';
                        buttonElement.style.pointerEvents = 'auto';
                        buttonElement.style.position = 'relative';
                        buttonElement.style.zIndex = '10000';
                        buttonElement.style.backgroundColor = '#f0f0f0';
                        buttonElement.style.border = '1px solid #ccc';
                        buttonElement.style.padding = '10px';
                        buttonElement.style.margin = '5px';
                        buttonElement.style.borderRadius = '5px';
                    }
                }
                
                // 创建重现步骤区域的容器
                var container = document.createElement('div');
                container.id = 'reproduction-steps-container';
                container.style.position = 'fixed';
                container.style.top = '20px';
                container.style.left = '20px';
                container.style.right = '20px';
                container.style.bottom = '100px';
                container.style.backgroundColor = '#ffffff';
                container.style.border = '3px solid #ff0000';
                container.style.borderRadius = '10px';
                container.style.padding = '20px';
                container.style.overflow = 'auto';
                container.style.zIndex = '9998';
                
                // 将重现步骤内容移动到容器中
                for (var p = 0; p < stepsElements.length; p++) {
                    if (stepsElements[p].parentElement) {
                        container.appendChild(stepsElements[p].cloneNode(true));
                    }
                }
                
                document.body.appendChild(container);
            """)
            
            self.log_signal.emit("已设置只显示重现步骤区域和底部操作按钮", False)
            
        except Exception as e:
            self.log_signal.emit(f"设置重现步骤区域显示失败: {e}", True)

    def _highlight_operation_area(self):
        """突出显示Bug详细和操作操作区域（底部操作按钮）"""
        try:
            # 定义底部操作按钮区域的选择器
            action_button_selectors = [
                # 底部操作栏
                '.action-panel',
                '.button-panel',
                '.operation-panel',
                '.main-actions',
                '.bug-actions',
                # 具体的按钮区域
                '.main-table .actions',
                '.detail-panel .actions',
                # 按钮容器
                '.btn-group',
                '.action-buttons',
                '.operation-buttons'
            ]
            
            # 尝试找到并突出显示操作按钮区域
            highlighted = False
            for selector in action_button_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        for element in elements:
                            # 添加红色边框和背景高亮
                            self.driver.execute_script("""
                                arguments[0].style.border = '3px solid #ff0000';
                                arguments[0].style.backgroundColor = '#fff5f5';
                                arguments[0].style.boxShadow = '0 0 10px rgba(255, 0, 0, 0.3)';
                                arguments[0].style.position = 'relative';
                                arguments[0].style.zIndex = '9999';
                                arguments[0].style.padding = '10px';
                                arguments[0].style.margin = '5px';
                            """, element)
                            highlighted = True
                            self.log_signal.emit(f"已突出显示Bug详细和操作操作区域: {selector}", False)
                except Exception as e:
                    continue
            
            if not highlighted:
                # 如果没有找到特定的按钮区域，尝试突出显示所有按钮
                buttons = self.driver.find_elements(By.CSS_SELECTOR, 'button, .btn, input[type="button"], input[type="submit"]')
                if buttons:
                    for button in buttons:
                        self.driver.execute_script("""
                            arguments[0].style.border = '2px solid #ff0000';
                            arguments[0].style.backgroundColor = '#fff5f5';
                            arguments[0].style.boxShadow = '0 0 5px rgba(255, 0, 0, 0.3)';
                        """, button)
                    self.log_signal.emit(f"已突出显示 {len(buttons)} 个操作按钮", False)
            
            # 添加操作提示
            self._add_operation_tips()
            
        except Exception as e:
            self.log_signal.emit(f"突出显示操作区域失败: {e}", True)

    def _add_operation_tips(self):
        """添加操作提示"""
        try:
            # 添加操作提示
            self.driver.execute_script("""
                var tip = document.createElement('div');
                tip.innerHTML = '<div style="position: fixed; top: 10px; right: 10px; background: #ff0000; color: white; padding: 10px; border-radius: 5px; z-index: 10000; font-weight: bold; max-width: 300px;">🔴 严格操作限制模式<br>• 只显示重现步骤区域<br>• 只能操作底部灰色按钮<br>• 其他区域完全禁用</div>';
                document.body.appendChild(tip);
                
                // 添加操作区域标识
                var areaTip = document.createElement('div');
                areaTip.innerHTML = '<div style="position: fixed; bottom: 10px; left: 10px; background: #ff0000; color: white; padding: 8px; border-radius: 5px; z-index: 10000; font-weight: bold;">✅ 重现步骤区域 - 底部灰色按钮可操作</div>';
                document.body.appendChild(areaTip);
                
                // 添加页面说明
                var pageTip = document.createElement('div');
                pageTip.innerHTML = '<div style="position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); background: #ff0000; color: white; padding: 15px; border-radius: 10px; z-index: 10000; font-weight: bold; text-align: center; max-width: 400px;">📋 当前显示：重现步骤区域（BUG重现步骤内容）<br>🔒 操作限制：只能操作底部灰色按钮<br>🚫 其他区域：完全隐藏且不可操作</div>';
                document.body.appendChild(pageTip);
                
                // 3秒后自动隐藏页面说明
                setTimeout(function() {
                    if (pageTip.parentNode) {
                        pageTip.parentNode.removeChild(pageTip);
                    }
                }, 3000);
            """)
            
            self.log_signal.emit("已添加操作提示和区域标识", False)
            
        except Exception as e:
            self.log_signal.emit(f"添加操作提示失败: {e}", True)

    def _debug_page_content(self):
        """调试：检查页面内容"""
        try:
            # 检查页面中的关键元素
            content_info = self.driver.execute_script("""
                var info = [];
                
                // 检查Bug详情相关元素
                var bugElements = document.querySelectorAll('.bug-description, .bug-steps, .bug-result, .bug-expect, .attachments, .history, .main-content, .bug-content, .bug-detail');
                info.push('Bug详情元素数量: ' + bugElements.length);
                
                for (var i = 0; i < bugElements.length; i++) {
                    var element = bugElements[i];
                    info.push('元素 ' + (i+1) + ': ' + element.className + ' - 可见性: ' + 
                             (element.style.display !== 'none' && element.style.visibility !== 'hidden' ? '可见' : '隐藏'));
                }
                
                // 检查文本内容
                var textElements = document.querySelectorAll('p, div, span, h1, h2, h3, h4, h5, h6');
                var visibleTextCount = 0;
                for (var j = 0; j < textElements.length; j++) {
                    var textElement = textElements[j];
                    if (textElement.style.display !== 'none' && textElement.style.visibility !== 'hidden' && textElement.textContent.trim() !== '') {
                        visibleTextCount++;
                    }
                }
                info.push('可见文本元素数量: ' + visibleTextCount);
                
                // 检查操作按钮
                var buttons = document.querySelectorAll('button, .btn, input[type="button"], input[type="submit"]');
                info.push('操作按钮数量: ' + buttons.length);
                
                return info;
            """)
            
            for info in content_info:
                self.log_signal.emit(f"调试信息: {info}", False)
                
        except Exception as e:
            self.log_signal.emit(f"调试页面内容失败: {e}", True)
