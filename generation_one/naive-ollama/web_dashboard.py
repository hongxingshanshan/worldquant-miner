from flask import Flask, render_template, jsonify, request, redirect, url_for
import json
import os
import time
import subprocess
import threading
import queue
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import requests
import sys
import ctypes
import signal
import atexit
import psutil
from requests.auth import HTTPBasicAuth

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# 导入数据库服务
try:
    from db.alpha_query_service import AlphaQueryService
    from db.alpha_sync_service import AlphaSyncService
    DB_AVAILABLE = True
except ImportError as e:
    print(f"数据库服务导入失败: {e}")
    DB_AVAILABLE = False

# 导入 API 处理函数
from api_handlers import register_api_routes

# 导入统一 Session 管理器
import sys
import os
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)
from common.wq_session_manager import get_wq_session_manager

app = Flask(__name__)

# Web Dashboard 不写入日志，只读取日志进行监控
# 使用标准 logging，不导入统一日志配置
import logging
logger = logging.getLogger(__name__)
# 设置为 WARNING 级别，只输出错误，不干扰主程序日志
logger.setLevel(logging.WARNING)

class AlphaDashboard:
    def __init__(self):
        self.status_file = "dashboard_status.json"
        self.log_file = "logs/app.log"  # 统一日志文件
        self.submission_log_file = "submission_log.json"
        self.results_dir = "results"
        self.logs_dir = "logs"
        self.credentials_path = "credential.txt"
        self.sess = None  # WorldQuant API session
        self.optimizer = None  # 延迟初始化

        # 数据库服务
        self.query_service = None
        self._init_db_service()

    def _init_db_service(self):
        """初始化数据库查询服务"""
        if not DB_AVAILABLE:
            return

        db_config_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'db', 'db_config.json')
        if os.path.exists(db_config_file):
            try:
                with open(db_config_file, 'r', encoding='utf-8') as f:
                    db_config = json.load(f)
                self.query_service = AlphaQueryService(db_config)
                logger.info("数据库查询服务初始化成功")
            except Exception as e:
                logger.warning(f"数据库查询服务初始化失败: {e}")

    def _load_config(self) -> Dict:
        """加载配置文件"""
        config_file = "config.json"
        default_config = {"model": "qwen2.5:14b"}

        if os.path.exists(config_file):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"加载配置文件失败: {e}")

        return default_config
        
    def get_system_status(self) -> Dict:
        """Get overall system status."""
        status = {
            "timestamp": datetime.now().isoformat(),
            "gpu": self.get_gpu_status(),
            "ollama": self.get_ollama_status(),
            "orchestrator": self.get_orchestrator_status(),
            "worldquant": self.get_worldquant_status(),
            "recent_activity": self.get_recent_activity(),
            "statistics": self.get_statistics()
        }
        return status
    
    def get_gpu_status(self) -> Dict:
        """Get GPU status and utilization."""
        try:
            # Try to get GPU info from nvidia-smi
            result = subprocess.run(['nvidia-smi', '--query-gpu=name,memory.used,memory.total,utilization.gpu,temperature.gpu', '--format=csv,noheader,nounits'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                if lines and lines[0]:
                    parts = lines[0].split(', ')
                    if len(parts) >= 5:
                        return {
                            "status": "active",
                            "name": parts[0],
                            "memory_used_mb": int(parts[1]),
                            "memory_total_mb": int(parts[2]),
                            "utilization_percent": int(parts[3]),
                            "temperature_c": int(parts[4]),
                            "memory_percent": round((int(parts[1]) / int(parts[2])) * 100, 1)
                        }
        except Exception as e:
            logger.warning(f"Could not get GPU status: {e}")
        
        return {"status": "unknown", "error": "GPU information not available"}
    
    def get_ollama_status(self) -> Dict:
        """Get Ollama service status."""
        try:
            response = requests.get("http://localhost:11434/api/tags", timeout=5)
            if response.status_code == 200:
                data = response.json()
                models = data.get("models", [])
                return {
                    "status": "running",
                    "models": [model.get("name", "") for model in models],
                    "model_count": len(models)
                }
        except Exception as e:
            logger.warning(f"Could not get Ollama status: {e}")
        
        return {"status": "not_responding", "error": "Ollama service not available"}
    
    def get_orchestrator_status(self) -> Dict:
        """Get orchestrator status from log files and process check."""
        status = {
            "status": "stopped",  # 默认为停止状态
            "last_activity": None,
            "current_mode": "continuous",
            "next_mining": None,
            "next_submission": None
        }

        try:
            # 首先检查进程是否在运行
            orchestrator_running = False
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    if 'python' in proc.info['name'].lower():
                        cmdline = ' '.join(proc.info['cmdline'] or [])
                        if 'alpha_orchestrator' in cmdline:
                            orchestrator_running = True
                            break
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            if orchestrator_running:
                status["status"] = "active"
            else:
                status["status"] = "stopped"

            # Read from local log file
            if os.path.exists(self.log_file):
                with open(self.log_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    if lines:
                        last_line = lines[-1].strip()
                        status["last_activity"] = last_line

                        # 如果进程在运行，检查日志中的错误
                        if orchestrator_running:
                            for line in reversed(lines[-50:]):
                                if any(keyword in line for keyword in ["Error", "Failed", "Exception"]):
                                    status["status"] = "error"
                                    break

                # Check submission schedule
                if os.path.exists(self.submission_log_file):
                    with open(self.submission_log_file, 'r') as f:
                        data = json.load(f)
                        last_submission = data.get("last_submission_date")
                        if last_submission:
                            last_date = datetime.fromisoformat(last_submission)
                            next_submission = last_date + timedelta(days=1)
                            next_submission = next_submission.replace(hour=14, minute=0, second=0, microsecond=0)
                            status["next_submission"] = next_submission.isoformat()

                # Calculate next mining time (every 6 hours)
                now = datetime.now()
                hours_since_midnight = now.hour + now.minute / 60
                next_mining_hour = ((int(hours_since_midnight // 6) + 1) * 6) % 24
                next_mining = now.replace(hour=int(next_mining_hour), minute=0, second=0, microsecond=0)
                if next_mining <= now:
                    next_mining += timedelta(days=1)
                status["next_mining"] = next_mining.isoformat()

        except Exception as e:
            logger.warning(f"Could not get orchestrator status: {e}")

        return status

    def get_worldquant_status(self) -> Dict:
        """Check WorldQuant Brain API status."""
        try:
            # 使用统一 Session 管理器
            sess = self._get_wq_session()
            if sess is not None:
                return {"status": "connected", "message": "Authentication successful"}
            else:
                return {"status": "auth_failed", "message": "Authentication failed"}
        except Exception as e:
            logger.warning(f"Could not check WorldQuant status: {e}")

        return {"status": "unknown", "message": "Could not verify connection"}
    
    def get_recent_activity(self) -> List[Dict]:
        """Get recent activity from log files."""
        activities = []

        try:
            # Read from local log file
            if os.path.exists(self.log_file):
                with open(self.log_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    # Get last 20 lines
                    for line in lines[-20:]:
                        line = line.strip()
                        if line and not line.startswith('---'):
                            try:
                                if ' - ' in line:
                                    timestamp_str, message = line.split(' - ', 1)
                                    timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                                    activities.append({
                                        "timestamp": timestamp.isoformat(),
                                        "message": message,
                                        "type": "info" if "INFO" in message else "error" if "ERROR" in message else "warning" if "WARNING" in message else "debug"
                                    })
                            except:
                                activities.append({
                                    "timestamp": datetime.now().isoformat(),
                                    "message": line,
                                    "type": "unknown"
                                })
        except Exception as e:
            logger.warning(f"Could not read recent activity: {e}")

        return activities[-10:]  # Return last 10 activities
    
    def get_statistics(self) -> Dict:
        """Get statistics about generated alphas and results."""
        stats = {
            "total_alphas_generated": 0,
            "simulations_completed": 0,
            "quality_alphas": 0,  # fitness > 0.5
            "failed_simulations": 0,
            "last_24h_generated": 0,
            "last_24h_completed": 0,
            "last_24h_quality": 0
        }

        try:
            # Count files in results directory
            if os.path.exists(self.results_dir):
                result_files = [f for f in os.listdir(self.results_dir) if f.endswith('.json')]
                stats["total_alphas_generated"] = len(result_files)

                # Count simulations and quality alphas
                for file in result_files:
                    file_path = os.path.join(self.results_dir, file)
                    try:
                        with open(file_path, 'r') as f:
                            data = json.load(f)
                            if data and len(data) > 0:
                                stats["simulations_completed"] += 1
                                # 检查 fitness
                                if isinstance(data, list):
                                    for item in data:
                                        if isinstance(item, dict):
                                            alpha_data = item.get("alpha_data", {})
                                            fitness = alpha_data.get("is", {}).get("fitness")
                                            if fitness is not None and fitness > 0.5:
                                                stats["quality_alphas"] += 1
                                                break  # 一个文件只计一次
                                elif isinstance(data, dict):
                                    alpha_data = data.get("alpha_data", {})
                                    fitness = alpha_data.get("is", {}).get("fitness")
                                    if fitness is not None and fitness > 0.5:
                                        stats["quality_alphas"] += 1
                            else:
                                stats["failed_simulations"] += 1
                    except:
                        stats["failed_simulations"] += 1

                # Count last 24 hours
                cutoff_time = datetime.now() - timedelta(hours=24)
                for file in result_files:
                    file_path = os.path.join(self.results_dir, file)
                    if os.path.getmtime(file_path) > cutoff_time.timestamp():
                        stats["last_24h_generated"] += 1
                        try:
                            with open(file_path, 'r') as f:
                                data = json.load(f)
                                if data and len(data) > 0:
                                    stats["last_24h_completed"] += 1
                                    # 检查 fitness
                                    if isinstance(data, list):
                                        for item in data:
                                            if isinstance(item, dict):
                                                alpha_data = item.get("alpha_data", {})
                                                fitness = alpha_data.get("is", {}).get("fitness")
                                                if fitness is not None and fitness > 0.5:
                                                    stats["last_24h_quality"] += 1
                                                    break
                                    elif isinstance(data, dict):
                                        alpha_data = data.get("alpha_data", {})
                                        fitness = alpha_data.get("is", {}).get("fitness")
                                        if fitness is not None and fitness > 0.5:
                                            stats["last_24h_quality"] += 1
                        except:
                            pass

        except Exception as e:
            logger.warning(f"Could not get statistics: {e}")

        return stats
    
    def get_logs(self, lines: int = 50) -> List[str]:
        """Get recent logs from log files."""
        logs = []
        try:
            # Read from local log file
            if os.path.exists(self.log_file):
                with open(self.log_file, 'r', encoding='utf-8') as f:
                    lines_list = f.readlines()
                    logs = lines_list[-lines:] if len(lines_list) > lines else lines_list
        except Exception as e:
            logger.warning(f"Could not read logs: {e}")

        return [line.strip() for line in logs if line.strip()]

    def get_alpha_generator_logs(self, lines: int = 50) -> List[str]:
        """Get alpha generator specific logs from unified log file."""
        logs = []
        try:
            if os.path.exists(self.log_file):
                with open(self.log_file, 'r', encoding='utf-8') as f:
                    all_logs = f.readlines()
                    # Filter for alpha generator/optimizer related logs by module name
                    alpha_logs = []
                    for line in all_logs:
                        # 日志格式: [模块名:文件名:行号]
                        if any(module in line for module in ['alpha_generator', 'alpha_optimizer', 'llm_client']):
                            alpha_logs.append(line)
                    logs = alpha_logs[-lines:] if len(alpha_logs) > lines else alpha_logs
        except Exception as e:
            logger.warning(f"Could not read alpha generator logs: {e}")

        return [line.strip() for line in logs if line.strip()]
    
    def trigger_mining(self) -> Dict:
        """Trigger manual alpha expression mining."""
        try:
            result = subprocess.run([
                "python", "alpha_orchestrator.py",
                "--mode", "miner",
                "--credentials", "./credential.txt"
            ], capture_output=True, text=True, timeout=1800)  # 30 分钟超时

            return {
                "success": result.returncode == 0,
                "output": result.stdout,
                "error": result.stderr
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def trigger_submission(self) -> Dict:
        """Trigger manual alpha submission."""
        try:
            result = subprocess.run([
                "python", "alpha_orchestrator.py",
                "--mode", "submitter",
                "--credentials", "./credential.txt",
                "--batch-size", "3"
            ], capture_output=True, text=True, timeout=5400)  # 90 分钟超时

            return {
                "success": result.returncode == 0,
                "output": result.stdout,
                "error": result.stderr
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def trigger_alpha_generation(self) -> Dict:
        """Trigger manual alpha generation."""
        try:
            result = subprocess.run([
                "python", "alpha_orchestrator.py",
                "--mode", "generator",
                "--credentials", "./credential.txt",
                "--batch-size", "1"
            ], capture_output=True, text=True, timeout=3600)  # 60 分钟超时

            return {
                "success": result.returncode == 0,
                "output": result.stdout,
                "error": result.stderr
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _get_wq_session(self, force_reauth: bool = False) -> Optional[requests.Session]:
        """获取 WorldQuant Brain API 会话，使用统一 Session 管理器"""
        if not hasattr(self, '_session_manager'):
            self._session_manager = get_wq_session_manager(self.credentials_path)
        self.sess = self._session_manager.get_session(force_reauth)
        return self.sess

    def get_simulation_status(self, sim_id: str) -> Dict:
        """获取模拟任务状态"""
        result = {
            "success": False,
            "data": None,
            "error": None
        }

        try:
            sess = self._get_wq_session()
            if sess is None:
                result["error"] = "无法连接到 WorldQuant Brain API"
                return result

            response = sess.get(
                f'https://api.worldquantbrain.com/simulations/{sim_id}',
                timeout=30
            )

            if response.status_code == 200:
                data = response.json()
                result["success"] = True
                result["data"] = self._format_simulation_data(data)
            elif response.status_code == 404:
                result["error"] = f"模拟任务不存在: {sim_id}"
            else:
                result["error"] = f"API 错误: {response.status_code}"
        except requests.exceptions.Timeout:
            result["error"] = "请求超时"
        except Exception as e:
            result["error"] = f"查询失败: {str(e)}"

        return result

    def get_alpha_details(self, alpha_id: str) -> Dict:
        """获取 Alpha 详细信息"""
        result = {
            "success": False,
            "data": None,
            "error": None
        }

        try:
            sess = self._get_wq_session()
            if sess is None:
                result["error"] = "无法连接到 WorldQuant Brain API"
                return result

            response = sess.get(
                f'https://api.worldquantbrain.com/alphas/{alpha_id}',
                timeout=30
            )

            if response.status_code == 200:
                data = response.json()
                formatted_data = self._format_alpha_data(data)
                if formatted_data:
                    result["success"] = True
                    result["data"] = formatted_data
                else:
                    result["error"] = "数据格式化失败"
            elif response.status_code == 404:
                result["error"] = f"Alpha 不存在: {alpha_id}"
            else:
                result["error"] = f"API 错误: {response.status_code}"
        except requests.exceptions.Timeout:
            result["error"] = "请求超时"
        except Exception as e:
            logger.error(f"获取 Alpha 详情失败: {e}")
            result["error"] = f"查询失败: {str(e)}"

        return result

    def _format_simulation_data(self, data: Dict) -> Dict:
        """格式化模拟任务数据为中文友好格式"""
        status_map = {
            "PENDING": "等待中",
            "RUNNING": "运行中",
            "COMPLETE": "已完成",
            "ERROR": "错误",
            "FAIL": "失败"
        }

        formatted = {
            "id": data.get("id", ""),
            "类型": data.get("type", ""),
            "状态": status_map.get(data.get("status", ""), data.get("status", "未知")),
            "原始状态": data.get("status", ""),
            "表达式": data.get("regular", ""),
            "alpha_id": data.get("alpha", ""),
            "设置": {
                "工具类型": data.get("settings", {}).get("instrumentType", ""),
                "区域": data.get("settings", {}).get("region", ""),
                "股票池": data.get("settings", {}).get("universe", ""),
                "延迟": data.get("settings", {}).get("delay", ""),
                "衰减": data.get("settings", {}).get("decay", ""),
                "中性化": data.get("settings", {}).get("neutralization", ""),
                "截断": data.get("settings", {}).get("truncation", ""),
            }
        }

        # 添加错误信息（如果有）
        if data.get("status") in ["ERROR", "FAIL"]:
            formatted["错误信息"] = data.get("message", "")
            # 添加参考链接
            links = data.get("links", {})
            if links:
                formatted["参考链接"] = links
            # 添加错误位置
            location = data.get("location", {})
            if location:
                formatted["错误位置"] = {
                    "行": location.get("line"),
                    "起始": location.get("start"),
                    "结束": location.get("end"),
                }

        return formatted

    def _format_alpha_data(self, data: Dict) -> Dict:
        """格式化 Alpha 数据为英文格式（与数据库格式一致）"""

        # 安全获取嵌套数据
        is_data = data.get("is") or {}
        os_data = data.get("os") or {}
        regular_data = data.get("regular") or {}
        settings_data = data.get("settings") or {}

        # 格式化检查项
        checks = []
        for check in is_data.get("checks", []) or []:
            checks.append({
                "check_name": check.get("name", "") or "",
                "result": check.get("result", "") or "",
                "limit_value": check.get("limit", "") or "",
                "actual_value": check.get("value", "") or ""
            })

        formatted = {
            "id": data.get("id", "") or "",
            "expression": regular_data.get("code", "") or "",
            "description": regular_data.get("description"),
            "grade": data.get("grade"),
            "status": data.get("status", "") or "",
            "stage": data.get("stage"),
            "date_created": data.get("dateCreated", "") or "",
            "date_submitted": data.get("dateSubmitted"),
            "date_modified": data.get("dateModified"),
            "operator_count": regular_data.get("operatorCount"),
            "settings": {
                "instrument_type": settings_data.get("instrumentType", "") or "",
                "region": settings_data.get("region", "") or "",
                "universe": settings_data.get("universe", "") or "",
                "delay": settings_data.get("delay"),
                "decay": settings_data.get("decay"),
                "neutralization": settings_data.get("neutralization", "") or "",
                "truncation": settings_data.get("truncation"),
                "start_date": settings_data.get("startDate", "") or "",
                "end_date": settings_data.get("endDate", "") or "",
            },
            "is": {
                "sharpe": is_data.get("sharpe"),
                "fitness": is_data.get("fitness"),
                "turnover": is_data.get("turnover"),
                "returns": is_data.get("returns"),
                "drawdown": is_data.get("drawdown"),
                "long_count": is_data.get("longCount"),
                "short_count": is_data.get("shortCount"),
                "pnl": is_data.get("pnl"),
                "book_size": is_data.get("bookSize"),
            },
            "os": {
                "sharpe": os_data.get("sharpe"),
                "fitness": os_data.get("fitness"),
                "turnover": os_data.get("turnover"),
            },
            "checks": checks,
            "classifications": [c.get("name", "") or "" for c in data.get("classifications", []) or []],
            "tags": data.get("tags", []) or [],
        }

        return formatted

    def _translate_check_name(self, name: str) -> str:
        """翻译检查项名称"""
        translations = {
            "LOW_SHARPE": "低夏普比率",
            "LOW_FITNESS": "低适应度",
            "LOW_TURNOVER": "低换手率",
            "HIGH_TURNOVER": "高换手率",
            "CONCENTRATED_WEIGHT": "权重集中",
            "LOW_SUB_UNIVERSE_SHARPE": "子股票池低夏普",
            "SELF_CORRELATION": "自相关性",
            "MATCHES_COMPETITION": "比赛匹配"
        }
        return translations.get(name, name)

    def get_failed_alphas(self, limit: int = 20) -> List[Dict]:
        """获取未通过检查的 Alpha 列表"""
        failed_alphas = []

        try:
            sess = self._get_wq_session()
            if sess is None:
                logger.warning("无法连接到 WorldQuant Brain API")
                return failed_alphas

            # 获取用户的 Alpha 列表，按 Sharpe 倒序排序
            response = sess.get(
                'https://api.worldquantbrain.com/users/self/alphas',
                params={
                    'limit': limit * 2,
                    'offset': 0,
                    'order': '-dateCreated',
                    'hidden': 'false'
                },
                timeout=30
            )

            if response.status_code == 200:
                data = response.json()
                alphas = data.get('results', [])

                for alpha in alphas:
                    is_data = alpha.get('is', {})
                    checks = is_data.get('checks', [])
                    status = alpha.get('status', '')

                    # 找出未通过的检查项
                    failed_checks = [c for c in checks if c.get('result') == 'FAIL']

                    # 判断是否可提交：status 不是 UNSUBMITTED 且所有检查通过
                    is_submittable = status != 'UNSUBMITTED' and all(
                        c.get('result') == 'PASS'
                        for c in checks
                    )

                    # 只保留未通过的 Alpha
                    if not is_submittable or failed_checks:
                        expression = alpha.get('regular', {}).get('code', '').strip()

                        alpha_info = {
                            "id": alpha.get('id', ''),
                            "expression": expression,
                            "sharpe": is_data.get('sharpe'),
                            "fitness": is_data.get('fitness'),
                            "turnover": is_data.get('turnover'),
                            "status": status,
                            "grade": alpha.get('grade', ''),
                            "date_created": alpha.get('dateCreated', ''),
                            "failed_checks": [self._translate_check_name(c.get('name', '')) for c in failed_checks],
                            "is_submittable": is_submittable
                        }
                        failed_alphas.append(alpha_info)

                        if len(failed_alphas) >= limit:
                            break

            else:
                logger.warning(f"获取 Alpha 列表失败: {response.status_code}")

        except requests.exceptions.Timeout:
            logger.error("获取失败 Alpha 列表超时")
        except Exception as e:
            logger.error(f"获取失败 Alpha 列表异常: {e}")

        return failed_alphas

    def optimize_alpha_by_id(self, alpha_id: str) -> Dict:
        """根据 Alpha ID 优化并提交 Alpha"""
        result = {
            "success": False,
            "original": None,
            "optimized": None,
            "failure_type": None,
            "task_id": None,
            "error": None
        }

        try:
            # 检查是否有可用的优化器
            if self.optimizer is None:
                # 延迟初始化优化器
                from alpha_optimizer import AlphaOptimizer
                from alpha_generator_ollama import AlphaGenerator

                # 创建 LLM 客户端
                generator = AlphaGenerator()
                self.optimizer = AlphaOptimizer(
                    llm_client=generator.llm_client,
                    wq_client=generator
                )

            # 调用优化并提交方法
            opt_result = self.optimizer.optimize_and_submit(alpha_id)

            if opt_result.get("success"):
                result["success"] = True
                result["original"] = opt_result.get("original")
                result["optimized"] = opt_result.get("optimized")
                result["failure_type"] = opt_result.get("failure_type")
                result["simulation_id"] = opt_result.get("simulation_id")
                result["alpha_id"] = alpha_id
                result["message"] = opt_result.get("message", "优化成功，已提交模拟测试")
            else:
                result["error"] = opt_result.get("error", "优化失败")
                result["alpha_id"] = alpha_id
                result["original"] = opt_result.get("original")
                result["optimized"] = opt_result.get("optimized")

        except Exception as e:
            logger.error(f"优化 Alpha {alpha_id} 失败: {e}")
            result["error"] = str(e)

        return result

    def submit_alpha_by_id(self, alpha_id: str) -> Dict:
        """提交 Alpha 到 WorldQuant Brain（带轮询监控）"""
        result = {
            "success": False,
            "alpha_id": alpha_id,
            "status": None,
            "message": None,
            "error": None
        }

        try:
            sess = self._get_wq_session()
            if sess is None:
                result["error"] = "无法连接到 WorldQuant Brain API"
                return result

            # 1. 发起提交请求
            url = f"https://api.worldquantbrain.com/alphas/{alpha_id}/submit"
            response = sess.post(url, timeout=30)

            if response.status_code == 409:
                result["success"] = True
                result["status"] = "ALREADY_SUBMITTED"
                result["message"] = "已提交过"
                return result

            if response.status_code == 403:
                # 403 通常是检查项未通过
                result["error"] = "提交被拒绝: Alpha 检查项未全部通过"
                try:
                    error_data = response.json()
                    checks = error_data.get("is", {}).get("checks", [])
                    failed_checks = [c.get("name") for c in checks if c.get("result") == "FAIL"]
                    pending_checks = [c.get("name") for c in checks if c.get("result") == "PENDING"]
                    if failed_checks:
                        result["error"] = f"提交被拒绝: 检查项未通过 - {', '.join(failed_checks)}"
                    elif pending_checks:
                        result["error"] = f"提交被拒绝: 检查项待定 - {', '.join(pending_checks)}"
                except:
                    pass
                return result

            if response.status_code not in [200, 201]:
                result["error"] = f"提交失败: HTTP {response.status_code}"
                try:
                    error_data = response.json()
                    if error_data.get("message"):
                        result["error"] = f"提交失败: {error_data['message']}"
                except:
                    pass
                return result

            # 2. 轮询监控提交状态
            logger.info(f"Alpha {alpha_id} 提交请求已接受，开始监控...")
            monitor_result = self._monitor_submission(alpha_id, sess, max_timeout_minutes=10)
            result.update(monitor_result)

        except requests.exceptions.Timeout:
            result["error"] = "请求超时"
        except Exception as e:
            logger.error(f"提交 Alpha {alpha_id} 失败: {e}")
            result["error"] = str(e)

        return result

    def submit_batch_alphas(self, limit: int = 10, dry_run: bool = False) -> Dict:
        """
        批量提交可提交的 Alpha

        Args:
            limit: 最大提交数量
            dry_run: 预检查模式，只返回可提交数量不实际提交

        Returns:
            提交结果
        """
        result = {
            "success": False,
            "submitted": [],
            "failed": [],
            "skipped": [],
            "total": 0,
            "submittable_count": 0,
            "error": None
        }

        try:
            # 1. 查询可提交的 Alpha
            submittable_alphas = self._get_submittable_alphas(limit)  # 多查一些备用
            result["submittable_count"] = len(submittable_alphas)

            if dry_run:
                result["success"] = True
                result["message"] = f"预检查完成，共有 {len(submittable_alphas)} 个可提交的 Alpha"
                return result

            if not submittable_alphas:
                result["success"] = True
                result["message"] = "没有可提交的 Alpha"
                return result

            # 2. 逐个提交（限制数量）
            to_submit = submittable_alphas[:limit]

            for alpha in to_submit:
                alpha_id = alpha['id']
                submit_result = self.submit_alpha_by_id(alpha_id)

                if submit_result.get('success'):
                    result["submitted"].append({
                        "id": alpha_id,
                        "status": submit_result.get('status'),
                        "message": submit_result.get('message')
                    })
                else:
                    result["failed"].append({
                        "id": alpha_id,
                        "error": submit_result.get('error', '未知错误')
                    })

                # 添加短暂延迟，避免请求过快
                time.sleep(1)

            result["total"] = len(result["submitted"])
            result["success"] = len(result["submitted"]) > 0

            # 如果全部失败，设置汇总错误信息
            if not result["success"] and result["failed"]:
                failed_errors = [f"{f['id']}: {f['error']}" for f in result["failed"][:3]]
                result["error"] = f"所有 Alpha 提交失败: {', '.join(failed_errors)}"
                if len(result["failed"]) > 3:
                    result["error"] += f" 等 {len(result['failed'])} 个"

        except Exception as e:
            logger.error(f"批量提交 Alpha 失败: {e}")
            result["error"] = str(e)

        return result

    def _get_submittable_alphas(self, limit: int = 50) -> List[Dict]:
        """
        获取可提交的 Alpha 列表

        Args:
            limit: 最大返回数量

        Returns:
            可提交的 Alpha 列表
        """
        if not self.query_service:
            return []

        try:
            sql = """
                SELECT a.id, a.expression, a.status, a.grade,
                       a.date_created, ap_is.sharpe as is_sharpe
                FROM alpha a
                LEFT JOIN alpha_performance ap_is ON a.id = ap_is.alpha_id AND ap_is.stage = 'IS'
                LEFT JOIN (
                    SELECT alpha_id,
                           SUM(CASE WHEN result = 'FAIL' THEN 1 ELSE 0 END) as is_checks_fail
                    FROM alpha_checks WHERE stage = 'IS'
                    GROUP BY alpha_id
                ) is_checks ON a.id = is_checks.alpha_id
                WHERE a.status = 'UNSUBMITTED'
                  AND (is_checks.is_checks_fail = 0 OR is_checks.is_checks_fail IS NULL)
                ORDER BY a.date_created DESC
                LIMIT %s
            """
            alphas = self.query_service.db.query_all(sql, (limit,))
            return alphas if alphas else []
        except Exception as e:
            logger.error(f"获取可提交 Alpha 列表失败: {e}")
            return []

    def get_submittable_count(self) -> Dict:
        """获取可提交 Alpha 数量"""
        result = {
            "success": False,
            "count": 0,
            "error": None
        }

        if not self.query_service:
            result["error"] = "数据库服务不可用"
            return result

        try:
            sql = """
                SELECT COUNT(*) as count
                FROM alpha a
                LEFT JOIN (
                    SELECT alpha_id,
                           SUM(CASE WHEN result = 'FAIL' THEN 1 ELSE 0 END) as is_checks_fail
                    FROM alpha_checks WHERE stage = 'IS'
                    GROUP BY alpha_id
                ) is_checks ON a.id = is_checks.alpha_id
                WHERE a.status = 'UNSUBMITTED'
                  AND (is_checks.is_checks_fail = 0 OR is_checks.is_checks_fail IS NULL)
            """
            count_result = self.query_service.db.query_one(sql)
            result["count"] = count_result['count'] if count_result else 0
            result["success"] = True
        except Exception as e:
            result["error"] = str(e)

        return result

    def _monitor_submission(self, alpha_id: str, sess, max_timeout_minutes: int = 10) -> Dict:
        """
        轮询监控提交状态

        Args:
            alpha_id: Alpha ID
            sess: requests Session
            max_timeout_minutes: 最大等待时间（分钟）

        Returns:
            监控结果
        """
        result = {
            "success": False,
            "alpha_id": alpha_id,
            "status": None,
            "message": None,
            "error": None
        }

        url = f"https://api.worldquantbrain.com/alphas/{alpha_id}/submit"
        start_time = time.time()
        max_timeout_seconds = max_timeout_minutes * 60
        base_sleep_time = 3
        max_sleep_time = 30
        attempt = 0

        while (time.time() - start_time) < max_timeout_seconds:
            attempt += 1
            elapsed_seconds = time.time() - start_time

            try:
                response = sess.get(url, timeout=30)

                # 404 表示已提交或不存在
                if response.status_code == 404:
                    result["success"] = True
                    result["status"] = "ALREADY_SUBMITTED"
                    result["message"] = "已提交过"
                    return result

                # 403 表示检查项未通过，需要解析详细信息
                if response.status_code == 403:
                    try:
                        error_data = response.json()
                        checks = error_data.get("is", {}).get("checks", [])
                        failed_checks = [c.get("name") for c in checks if c.get("result") == "FAIL"]
                        pending_checks = [c.get("name") for c in checks if c.get("result") == "PENDING"]
                        if failed_checks:
                            result["error"] = f"提交被拒绝: 检查项未通过 - {', '.join(failed_checks)}"
                        elif pending_checks:
                            result["error"] = f"提交被拒绝: 检查项待定 - {', '.join(pending_checks)}"
                        else:
                            result["error"] = "提交被拒绝: Alpha 检查项未全部通过"
                    except:
                        result["error"] = "提交被拒绝: Alpha 检查项未全部通过"
                    return result

                if response.status_code != 200:
                    result["error"] = f"监控失败: HTTP {response.status_code}"
                    return result

                # 空响应表示仍在提交中
                if not response.text or not response.text.strip():
                    sleep_time = min(base_sleep_time * (1.5 ** (attempt - 1)), max_sleep_time)
                    logger.info(f"Alpha {alpha_id} 提交中... 等待 {sleep_time:.1f}s (已等待 {elapsed_seconds:.0f}s)")
                    time.sleep(sleep_time)
                    continue

                # 尝试解析 JSON（提交完成）
                try:
                    data = response.json()
                    logger.info(f"Alpha {alpha_id} 提交完成: {data}")

                    # 检查返回数据中的状态
                    if isinstance(data, dict):
                        # 检查是否有错误信息
                        if data.get("error"):
                            result["error"] = data.get("error")
                            return result

                        # 检查 is.checks 中的失败项
                        is_data = data.get("is", {})
                        checks = is_data.get("checks", [])
                        failed_checks = [c.get("name") for c in checks if c.get("result") == "FAIL"]
                        pending_checks = [c.get("name") for c in checks if c.get("result") == "PENDING"]

                        if failed_checks:
                            result["error"] = f"提交被拒绝: 检查项未通过 - {', '.join(failed_checks)}"
                            return result

                        if pending_checks:
                            result["error"] = f"提交被拒绝: 检查项待定 - {', '.join(pending_checks)}"
                            return result

                        # 检查提交状态
                        status = data.get("status", "")
                        if status == "SUBMITTED":
                            result["success"] = True
                            result["status"] = "SUBMITTED"
                            result["message"] = "提交成功"
                        elif status == "UNSUBMITTED":
                            # 未提交状态，可能是检查未通过
                            result["error"] = "提交失败: Alpha 仍处于未提交状态"
                        else:
                            result["success"] = True
                            result["status"] = status or "SUBMITTED"
                            result["message"] = "提交完成"

                    return result

                except json.JSONDecodeError:
                    # 非 JSON 响应，继续等待
                    sleep_time = min(base_sleep_time * (1.5 ** (attempt - 1)), max_sleep_time)
                    time.sleep(sleep_time)
                    continue

            except requests.exceptions.Timeout:
                logger.warning(f"监控请求超时 (attempt {attempt})")
                sleep_time = min(base_sleep_time * 2, max_sleep_time)
                time.sleep(sleep_time)
                continue

            except Exception as e:
                logger.warning(f"监控请求失败 (attempt {attempt}): {e}")
                sleep_time = min(base_sleep_time * 2, max_sleep_time)
                time.sleep(sleep_time)
                continue

        # 超时
        result["error"] = f"提交监控超时（等待超过 {max_timeout_minutes} 分钟）"
        return result

    # ==================== 数据库相关方法 ====================

    def get_alphas_from_db(self, limit: int = 50, order_by: str = 'is_checks_pass',
                           status_filter: str = None, stage_filter: str = None) -> List[Dict]:
        """从数据库获取 Alpha 列表"""
        if not self.query_service:
            return []

        try:
            alphas = self.query_service.get_alpha_list(
                limit=limit,
                order_by=order_by,
                status_filter=status_filter,
                stage_filter=stage_filter
            )

            # 格式化返回
            result = []
            for a in alphas:
                result.append({
                    "id": a['id'],
                    "expression": a['expression'],
                    "description": a['description'],
                    "grade": a['grade'],
                    "status": a['status'],
                    "stage": a['stage'],
                    "is_submitted": a['status'] != 'UNSUBMITTED' if a['status'] else False,
                    "date_created": str(a['date_created']) if a['date_created'] else None,
                    "date_submitted": str(a['date_submitted']) if a['date_submitted'] else None,
                    "date_modified": str(a['date_modified']) if a['date_modified'] else None,
                    "synced_at": str(a['synced_at']) if a['synced_at'] else None,
                    "operator_count": a['operator_count'],
                    # IS 指标
                    "is_sharpe": float(a['is_sharpe']) if a['is_sharpe'] else None,
                    "is_fitness": float(a['is_fitness']) if a['is_fitness'] else None,
                    "is_turnover": float(a['is_turnover']) if a['is_turnover'] else None,
                    "is_returns": float(a['is_returns']) if a['is_returns'] else None,
                    "is_drawdown": float(a['is_drawdown']) if a['is_drawdown'] else None,
                    # OS 指标
                    "os_sharpe": float(a['os_sharpe']) if a['os_sharpe'] else None,
                    "os_fitness": float(a['os_fitness']) if a['os_fitness'] else None,
                    "os_turnover": float(a['os_turnover']) if a['os_turnover'] else None,
                    # 检查结果统计
                    "is_checks_pass": a['is_checks_pass'] or 0,
                    "is_checks_fail": a['is_checks_fail'] or 0,
                    "os_checks_pass": a['os_checks_pass'] or 0,
                    "os_checks_fail": a['os_checks_fail'] or 0,
                    # 可提交判断
                    "is_submittable": (a['is_checks_fail'] or 0) == 0 and a['status'] == 'UNSUBMITTED' if a['status'] else False
                })

            return {"data": result, "pagination": {"page": 1, "page_size": limit, "total": len(result), "total_pages": 1}}
        except Exception as e:
            logger.error(f"从数据库获取 Alpha 列表失败: {e}")
            return {"data": [], "pagination": {"page": 1, "page_size": limit, "total": 0, "total_pages": 0}}

    def get_alphas_from_db_paginated(self, page: int = 1, page_size: int = 20,
                                      order_by: str = 'is_checks_pass',
                                      status_filter: str = None,
                                      date_from: str = None,
                                      date_to: str = None,
                                      submittable_only: bool = False) -> Dict:
        """从数据库获取 Alpha 列表（支持分页和筛选）"""
        result = {
            "data": [],
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total": 0,
                "total_pages": 0
            }
        }

        if not self.query_service:
            return result

        try:
            # 构建查询条件
            where_clauses = []
            params = []

            if status_filter:
                where_clauses.append("a.status = %s")
                params.append(status_filter)

            if date_from:
                where_clauses.append("a.date_created >= %s")
                params.append(date_from)

            if date_to:
                where_clauses.append("a.date_created <= %s")
                params.append(date_to + " 23:59:59")

            if submittable_only:
                where_clauses.append("is_checks.is_checks_fail = 0")
                where_clauses.append("a.status = 'UNSUBMITTED'")

            where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

            # 查询总数
            count_sql = f"""
                SELECT COUNT(*) as total
                FROM alpha a
                LEFT JOIN alpha_performance ap_is ON a.id = ap_is.alpha_id AND ap_is.stage = 'IS'
                LEFT JOIN (
                    SELECT alpha_id,
                           SUM(CASE WHEN result = 'PASS' THEN 1 ELSE 0 END) as is_checks_pass,
                           SUM(CASE WHEN result = 'FAIL' THEN 1 ELSE 0 END) as is_checks_fail
                    FROM alpha_checks WHERE stage = 'IS'
                    GROUP BY alpha_id
                ) is_checks ON a.id = is_checks.alpha_id
                WHERE {where_sql}
            """
            count_result = self.query_service.db.query_one(count_sql, tuple(params))
            total = count_result['total'] if count_result else 0

            # 计算分页
            total_pages = (total + page_size - 1) // page_size if total > 0 else 1
            offset = (page - 1) * page_size

            # 排序映射
            order_map = {
                'is_checks_pass': 'is_checks.is_checks_fail ASC, is_checks.is_checks_pass DESC, a.date_created DESC',
                'date_created': 'a.date_created DESC',
                'is_sharpe': 'ap_is.sharpe DESC',
                'is_fitness': 'ap_is.fitness DESC'
            }
            order_sql = order_map.get(order_by, 'is_checks.is_checks_fail ASC, is_checks.is_checks_pass DESC, a.date_created DESC')

            # 查询数据
            sql = f"""
                SELECT a.*,
                       ap_is.sharpe as is_sharpe, ap_is.fitness as is_fitness,
                       ap_is.turnover as is_turnover, ap_is.returns as is_returns,
                       ap_is.drawdown as is_drawdown,
                       is_checks.is_checks_pass, is_checks.is_checks_fail,
                       ap_os.sharpe as os_sharpe, ap_os.fitness as os_fitness,
                       ap_os.turnover as os_turnover,
                       os_checks.os_checks_pass, os_checks.os_checks_fail,
                       s.instrument_type, s.region, s.universe, s.delay, s.decay,
                       s.neutralization, s.truncation
                FROM alpha a
                LEFT JOIN alpha_settings s ON a.id = s.alpha_id
                LEFT JOIN alpha_performance ap_is ON a.id = ap_is.alpha_id AND ap_is.stage = 'IS'
                LEFT JOIN alpha_performance ap_os ON a.id = ap_os.alpha_id AND ap_os.stage = 'OS'
                LEFT JOIN (
                    SELECT alpha_id,
                           SUM(CASE WHEN result = 'PASS' THEN 1 ELSE 0 END) as is_checks_pass,
                           SUM(CASE WHEN result = 'FAIL' THEN 1 ELSE 0 END) as is_checks_fail
                    FROM alpha_checks WHERE stage = 'IS'
                    GROUP BY alpha_id
                ) is_checks ON a.id = is_checks.alpha_id
                LEFT JOIN (
                    SELECT alpha_id,
                           SUM(CASE WHEN result = 'PASS' THEN 1 ELSE 0 END) as os_checks_pass,
                           SUM(CASE WHEN result = 'FAIL' THEN 1 ELSE 0 END) as os_checks_fail
                    FROM alpha_checks WHERE stage = 'OS'
                    GROUP BY alpha_id
                ) os_checks ON a.id = os_checks.alpha_id
                WHERE {where_sql}
                ORDER BY {order_sql}
                LIMIT %s OFFSET %s
            """
            params.extend([page_size, offset])

            alphas = self.query_service.db.query_all(sql, tuple(params))

            # 格式化返回
            formatted = []
            for a in alphas:
                formatted.append({
                    "id": a['id'],
                    "expression": a['expression'],
                    "description": a['description'],
                    "grade": a['grade'],
                    "status": a['status'],
                    "stage": a['stage'],
                    "is_submitted": a['status'] != 'UNSUBMITTED' if a['status'] else False,
                    "date_created": str(a['date_created']) if a['date_created'] else None,
                    "date_submitted": str(a['date_submitted']) if a['date_submitted'] else None,
                    "date_modified": str(a['date_modified']) if a['date_modified'] else None,
                    "synced_at": str(a['synced_at']) if a['synced_at'] else None,
                    "operator_count": a['operator_count'],
                    # IS 指标
                    "is_sharpe": float(a['is_sharpe']) if a['is_sharpe'] else None,
                    "is_fitness": float(a['is_fitness']) if a['is_fitness'] else None,
                    "is_turnover": float(a['is_turnover']) if a['is_turnover'] else None,
                    "is_returns": float(a['is_returns']) if a['is_returns'] else None,
                    "is_drawdown": float(a['is_drawdown']) if a['is_drawdown'] else None,
                    # OS 指标
                    "os_sharpe": float(a['os_sharpe']) if a['os_sharpe'] else None,
                    "os_fitness": float(a['os_fitness']) if a['os_fitness'] else None,
                    "os_turnover": float(a['os_turnover']) if a['os_turnover'] else None,
                    # 检查结果统计
                    "is_checks_pass": a['is_checks_pass'] or 0,
                    "is_checks_fail": a['is_checks_fail'] or 0,
                    "os_checks_pass": a['os_checks_pass'] or 0,
                    "os_checks_fail": a['os_checks_fail'] or 0,
                    # 可提交判断
                    "is_submittable": (a['is_checks_fail'] or 0) == 0 and a['status'] == 'UNSUBMITTED' if a['status'] else False
                })

            result["data"] = formatted
            result["pagination"] = {
                "page": page,
                "page_size": page_size,
                "total": total,
                "total_pages": total_pages
            }

        except Exception as e:
            logger.error(f"从数据库获取 Alpha 列表失败: {e}")

        return result

    def get_alpha_detail_from_db(self, alpha_id: str) -> Dict:
        """从数据库获取 Alpha 详情（返回英文格式）"""
        from decimal import Decimal

        result = {
            "success": False,
            "data": None,
            "error": None
        }

        if not self.query_service:
            result["error"] = "数据库服务不可用"
            return result

        try:
            alpha = self.query_service.get_alpha_detail(alpha_id)

            if not alpha:
                result["error"] = f"Alpha 不存在: {alpha_id}"
                return result

            # 格式化检查结果
            failed_checks = [c['check_name'] for c in alpha['checks'] if c['result'] == 'FAIL']

            # 转换 Decimal 为 float
            def convert_decimal(obj):
                if isinstance(obj, Decimal):
                    return float(obj)
                elif isinstance(obj, dict):
                    return {k: convert_decimal(v) for k, v in obj.items()}
                elif isinstance(obj, list):
                    return [convert_decimal(item) for item in obj]
                return obj

            # 转换性能指标
            performances = alpha['performances']
            is_perf = convert_decimal(performances.get('IS'))
            os_perf = convert_decimal(performances.get('OS'))
            train_perf = convert_decimal(performances.get('TRAIN'))
            test_perf = convert_decimal(performances.get('TEST'))
            prod_perf = convert_decimal(performances.get('PROD'))

            result["success"] = True
            result["data"] = {
                "id": alpha['id'],
                "expression": alpha['expression'],
                "description": alpha['description'],
                "grade": alpha['grade'],
                "status": alpha['status'],
                "stage": alpha['stage'],
                "date_created": str(alpha['date_created']) if alpha.get('date_created') else None,
                "date_submitted": str(alpha['date_submitted']) if alpha.get('date_submitted') else None,
                "date_modified": str(alpha['date_modified']) if alpha.get('date_modified') else None,
                "synced_at": str(alpha['synced_at']) if alpha.get('synced_at') else None,
                "operator_count": alpha['operator_count'],
                "settings": convert_decimal(alpha['settings']),
                "is": is_perf,
                "os": os_perf,
                "train": train_perf,
                "test": test_perf,
                "prod": prod_perf,
                "checks": convert_decimal(alpha['checks']),
                "failed_checks": failed_checks,
                "competitions": convert_decimal(alpha.get('competitions', [])),
                "team": convert_decimal(alpha.get('team')),
                "is_submittable": len(failed_checks) == 0 and alpha['status'] == 'UNSUBMITTED' if alpha['status'] else False
            }

        except Exception as e:
            logger.error(f"从数据库获取 Alpha 详情失败: {e}")
            result["error"] = str(e)

        return result

    def sync_incremental(self) -> Dict:
        """触发增量同步"""
        result = {
            "success": False,
            "stats": None,
            "error": None
        }

        try:
            # 获取数据库配置
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            db_config_file = os.path.join(project_root, 'db', 'db_config.json')
            credentials_path = os.path.join(project_root, 'credential.txt')

            with open(db_config_file, 'r', encoding='utf-8') as f:
                db_config = json.load(f)

            sync_service = AlphaSyncService(credentials_path, db_config)
            stats = sync_service.sync_incremental(batch_size=50)

            result["success"] = True
            result["stats"] = stats

        except Exception as e:
            logger.error(f"增量同步失败: {e}")
            result["error"] = str(e)

        return result

    def sync_full(self) -> Dict:
        """触发全量同步"""
        result = {
            "success": False,
            "stats": None,
            "error": None
        }

        try:
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            db_config_file = os.path.join(project_root, 'db', 'db_config.json')
            credentials_path = os.path.join(project_root, 'credential.txt')

            with open(db_config_file, 'r', encoding='utf-8') as f:
                db_config = json.load(f)

            sync_service = AlphaSyncService(credentials_path, db_config)
            stats = sync_service.sync_all(batch_size=50)

            result["success"] = True
            result["stats"] = stats

        except Exception as e:
            logger.error(f"全量同步失败: {e}")
            result["error"] = str(e)

        return result

    def get_sync_status(self) -> Dict:
        """获取同步状态"""
        if not self.query_service:
            return {"error": "数据库服务不可用"}

        try:
            return {
                "last_sync_time": str(self.query_service.get_last_sync_time()) if self.query_service.get_last_sync_time() else None,
                "last_created_time": str(self.query_service.get_last_created_time()) if self.query_service.get_last_created_time() else None,
                "total_alphas": self.query_service.get_alpha_count(),
                "statistics": self.query_service.get_statistics()
            }
        except Exception as e:
            return {"error": str(e)}

# Global dashboard instance
dashboard = AlphaDashboard()

# 注册 API 路由
register_api_routes(app, dashboard)


def setup_cleanup_handler():
    """设置 Windows 控制台关闭事件处理器"""
    def cleanup():
        logger.info("Web Dashboard 正在关闭...")
        # Flask 服务器会自动处理关闭

    def signal_handler(signum=None, frame=None):
        logger.info("收到退出信号，正在关闭...")
        cleanup()
        sys.exit(0)

    # 注册信号处理
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Windows 平台特殊处理
    if sys.platform == 'win32':
        try:
            CTRL_HANDLER_TYPE = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_uint)

            def console_ctrl_handler(ctrl_type):
                if ctrl_type in (2, 5, 6):
                    logger.info(f"收到 Windows 控制台关闭事件 (类型: {ctrl_type})，正在关闭...")
                    cleanup()
                    return True
                return False

            handler = CTRL_HANDLER_TYPE(console_ctrl_handler)
            ctypes.windll.kernel32.SetConsoleCtrlHandler(handler, True)
            logger.info("已注册 Windows 控制台关闭事件处理器")
        except Exception as e:
            logger.warning(f"无法注册 Windows 控制台事件处理器: {e}")

    atexit.register(cleanup)

if __name__ == '__main__':
    # 设置清理处理器
    setup_cleanup_handler()

    # Create templates directory if it doesn't exist
    os.makedirs('templates', exist_ok=True)

    print("Starting Alpha Generator Dashboard...")
    print("Dashboard will be available at: http://localhost:5000")
    print("Ollama API: http://localhost:11434")

    app.run(host='0.0.0.0', port=5000, debug=True)
