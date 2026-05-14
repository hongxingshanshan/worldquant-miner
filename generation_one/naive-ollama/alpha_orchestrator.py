import argparse
import requests
import json
import os
import time
import schedule
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from requests.auth import HTTPBasicAuth
import subprocess
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import queue
import signal
import atexit
import ctypes
import logging

# 导入配置管理器
try:
    from config_manager import get_config_manager, ConfigManager, Config
    CONFIG_AVAILABLE = True
except ImportError:
    CONFIG_AVAILABLE = False

# 导入统一 LLM 客户端
try:
    from llm_client import LLMClient
    LLM_CLIENT_AVAILABLE = True
except ImportError:
    LLM_CLIENT_AVAILABLE = False

# 导入模型舰队管理器
try:
    from model_fleet_manager import ModelFleetManager, ModelInfo
    MODEL_FLEET_AVAILABLE = True
except ImportError:
    MODEL_FLEET_AVAILABLE = False

# 导入统一 Session 管理器
import sys
import os
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)
from common.wq_session_manager import get_wq_session_manager

# 使用统一日志配置（多进程安全）
try:
    from logging_config import get_logger, setup_mp_logging, shutdown_mp_logging
    logger = get_logger(__name__)
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

if not CONFIG_AVAILABLE:
    logger.warning("config_manager 模块未找到，使用默认配置")

if not MODEL_FLEET_AVAILABLE:
    logger.warning("model_fleet_manager 模块未找到，VRAM 管理功能不可用")

class AlphaOrchestrator:
    def __init__(self, credentials_path: str, ollama_url: str = "http://localhost:11434",
                 config_path: Optional[str] = None, model_override: Optional[str] = None):
        self.credentials_path = credentials_path
        self.ollama_url = ollama_url
        self.config_path = config_path
        self.model_override = model_override

        # 使用统一 Session 管理器
        self._session_manager = get_wq_session_manager(credentials_path)
        self.sess = self._session_manager.get_session()
        if self.sess is None:
            raise Exception("无法通过统一 Session 管理器认证 WorldQuant Brain")
        logger.info("使用统一 Session 管理器认证成功")

        self.last_submission_date = None
        self.submission_log_file = "submission_log.json"
        self.load_submission_history()

        # 加载配置
        self.config = None
        if CONFIG_AVAILABLE:
            self.config_manager = get_config_manager(config_path)
            self.config = self.config_manager.config

        # 初始化统一 LLM 客户端
        self.llm_client = None
        self.use_online_llm = False
        if LLM_CLIENT_AVAILABLE:
            try:
                self.llm_client = LLMClient(config_path)
                self.use_online_llm = self.llm_client.is_online()
                logger.info(f"LLM 客户端初始化成功 - 提供商: {self.llm_client.get_provider()}, 模型: {self.llm_client.get_model_name()}")
            except Exception as e:
                logger.warning(f"LLM 客户端初始化失败: {e}")

        # Concurrency control
        self.max_concurrent_simulations = self.config.max_concurrent if self.config else 3
        self.simulation_semaphore = threading.Semaphore(self.max_concurrent_simulations)
        self.running = True
        self.generator_process = None
        self.miner_process = None
        self._child_processes = []  # 跟踪所有子进程

        # Model fleet management (仅 Ollama 模式需要)
        self.model_fleet_manager = None
        self.vram_monitoring_active = False
        self.vram_monitor_thread = None

        if not self.use_online_llm:
            self.model_fleet_manager = ModelFleetManager(ollama_url, config_path, model_override)
            logger.info("使用 Ollama 本地模型，启用 VRAM 监控")
        else:
            logger.info("使用线上大模型，跳过 VRAM 监控")

        # Restart mechanism
        self.restart_interval = 1800  # 30 minutes in seconds
        self.last_restart_time = time.time()
        self.restart_thread = None

        # 注册退出清理函数
        self._setup_cleanup_handlers()

    def _setup_cleanup_handlers(self):
        """设置退出时的清理处理器"""
        def cleanup_handler(signum=None, frame=None):
            logger.info("收到退出信号，正在清理子进程...")
            self.cleanup_child_processes()
            sys.exit(0)

        # 注册信号处理
        signal.signal(signal.SIGINT, cleanup_handler)
        signal.signal(signal.SIGTERM, cleanup_handler)

        # Windows 平台特殊处理：捕获控制台关闭事件
        if sys.platform == 'win32':
            try:
                # 定义控制台事件类型
                CTRL_HANDLER_TYPE = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_uint)

                # 保存 handler 引用，防止被垃圾回收
                self._ctrl_handler = None

                def console_ctrl_handler(ctrl_type):
                    """处理 Windows 控制台事件"""
                    # CTRL_CLOSE_EVENT = 2, CTRL_LOGOFF_EVENT = 5, CTRL_SHUTDOWN_EVENT = 6
                    if ctrl_type in (2, 5, 6):
                        # 使用 print 而不是 logger，因为 logger 可能已经不可用
                        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 收到 Windows 控制台关闭事件 (类型: {ctrl_type})，正在清理子进程...")
                        # 强制刷新输出
                        sys.stdout.flush()
                        self.cleanup_child_processes()
                        return True
                    return False

                # 设置控制台处理器
                self._ctrl_handler = CTRL_HANDLER_TYPE(console_ctrl_handler)
                result = ctypes.windll.kernel32.SetConsoleCtrlHandler(self._ctrl_handler, True)
                if result:
                    logger.info("已注册 Windows 控制台关闭事件处理器")
                else:
                    logger.warning("注册 Windows 控制台事件处理器失败")
            except Exception as e:
                logger.warning(f"无法注册 Windows 控制台事件处理器: {e}")

        # 注册 atexit 处理器（用于正常退出）
        atexit.register(self.cleanup_child_processes)

    def cleanup_child_processes(self):
        """清理所有子进程"""
        self.running = False

        # 终止 generator_process
        if self.generator_process and self.generator_process.poll() is None:
            logger.info(f"正在终止 generator_process (PID: {self.generator_process.pid})")
            try:
                self.generator_process.terminate()
                self.generator_process.wait(timeout=5)
            except:
                try:
                    self.generator_process.kill()
                except:
                    pass

        # 终止 miner_process
        if self.miner_process and self.miner_process.poll() is None:
            logger.info(f"正在终止 miner_process (PID: {self.miner_process.pid})")
            try:
                self.miner_process.terminate()
                self.miner_process.wait(timeout=5)
            except:
                try:
                    self.miner_process.kill()
                except:
                    pass

        # 终止所有跟踪的子进程
        for proc in self._child_processes:
            if proc.poll() is None:
                logger.info(f"正在终止子进程 (PID: {proc.pid})")
                try:
                    proc.terminate()
                    proc.wait(timeout=3)
                except:
                    try:
                        proc.kill()
                    except:
                        pass

        self._child_processes.clear()
        logger.info("所有子进程已清理")

    def load_submission_history(self):
        """Load submission history to track daily submissions."""
        if os.path.exists(self.submission_log_file):
            try:
                with open(self.submission_log_file, 'r') as f:
                    data = json.load(f)
                    self.last_submission_date = data.get('last_submission_date')
                    logger.info(f"Loaded submission history. Last submission: {self.last_submission_date}")
            except Exception as e:
                logger.warning(f"Could not load submission history: {e}")
                self.last_submission_date = None
        else:
            self.last_submission_date = None

    def save_submission_history(self):
        """Save submission history."""
        data = {
            'last_submission_date': self.last_submission_date,
            'updated_at': datetime.now().isoformat()
        }
        with open(self.submission_log_file, 'w') as f:
            json.dump(data, f, indent=2)

    def start_vram_monitoring(self):
        """Start VRAM monitoring in a separate thread."""
        if self.vram_monitoring_active:
            logger.info("VRAM monitoring already active")
            return
        
        self.vram_monitoring_active = True
        self.vram_monitor_thread = threading.Thread(target=self._vram_monitor_loop, daemon=True)
        self.vram_monitor_thread.start()
        logger.info("Started VRAM monitoring thread")

    def stop_vram_monitoring(self):
        """Stop VRAM monitoring."""
        self.vram_monitoring_active = False
        if self.vram_monitor_thread:
            self.vram_monitor_thread.join(timeout=5)
        logger.info("Stopped VRAM monitoring")

    def _vram_monitor_loop(self):
        """VRAM monitoring loop that checks for errors and handles model downgrading."""
        logger.info("VRAM monitoring loop started")
        
        while self.vram_monitoring_active and self.running:
            try:
                # Check for VRAM errors in recent logs
                if self._check_for_vram_errors():
                    logger.warning("VRAM error detected in monitoring loop")
                    if self.model_fleet_manager.handle_vram_error():
                        logger.info("Model fleet action taken due to VRAM issues")
                        # Restart the alpha generator with new model configuration
                        self._restart_alpha_generator()
                
                time.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"Error in VRAM monitoring loop: {e}")
                time.sleep(60)  # Wait longer on error
        
        logger.info("VRAM monitoring loop stopped")

    def _check_for_vram_errors(self) -> bool:
        """Check recent logs for VRAM errors."""
        try:
            # Check Ollama logs and application logs for VRAM errors
            log_files_to_check = [
                '/app/logs/ollama.log',  # Ollama logs redirected to file
                'alpha_orchestrator.log',
                'alpha_generator_ollama.log'
            ]
            
            for log_file in log_files_to_check:
                try:
                    if os.path.exists(log_file):
                        # Read last 50 lines of log file
                        with open(log_file, 'r') as f:
                            lines = f.readlines()
                            recent_lines = lines[-50:] if len(lines) > 50 else lines
                            
                            for line in recent_lines:
                                if self.model_fleet_manager.detect_vram_error(line):
                                    logger.warning(f"VRAM error found in {log_file}: {line.strip()}")
                                    return True
                except Exception as e:
                    # Skip files that can't be read
                    continue
            
            return False
        except Exception as e:
            logger.error(f"Error checking for VRAM errors: {e}")
            return False

    def _restart_alpha_generator(self):
        """Restart the alpha generator with the new model."""
        try:
            logger.info("Restarting alpha generator with new model")
            
            # Stop current generator process if running
            if self.generator_process and self.generator_process.poll() is None:
                self.generator_process.terminate()
                self.generator_process.wait(timeout=30)
            
            # Start new generator process in continuous mode
            self.start_alpha_generator_continuous(batch_size=3, sleep_time=30)
            
        except Exception as e:
            logger.error(f"Error restarting alpha generator: {e}")
    
    def start_restart_monitoring(self):
        """Start restart monitoring in a separate thread."""
        if not self.restart_thread or not self.restart_thread.is_alive():
            self.restart_thread = threading.Thread(target=self._restart_monitor_loop, daemon=True)
            self.restart_thread.start()
            logger.info("🔄 Restart monitoring started (30-minute intervals)")
    
    def _restart_monitor_loop(self):
        """Monitor and restart processes every 30 minutes."""
        while self.running:
            try:
                current_time = time.time()
                time_since_last_restart = current_time - self.last_restart_time
                
                if time_since_last_restart >= self.restart_interval:
                    logger.info(f"⏰ 30 minutes elapsed since last restart, initiating restart...")
                    self.restart_all_processes()
                else:
                    remaining_time = self.restart_interval - time_since_last_restart
                    logger.debug(f"⏰ Next restart in {remaining_time/60:.1f} minutes")
                
                # Check every minute
                time.sleep(60)
                
            except Exception as e:
                logger.error(f"Error in restart monitoring: {e}")
                time.sleep(60)

    def get_model_fleet_status(self) -> Dict:
        """Get the current status of the model fleet."""
        return self.model_fleet_manager.get_fleet_status()

    def reset_model_fleet(self):
        """Reset the model fleet to the largest model."""
        return self.model_fleet_manager.reset_to_largest_model()

    def force_model_downgrade(self):
        """Force downgrade to the next smaller model."""
        return self.model_fleet_manager.downgrade_model()
    
    def force_application_reset(self):
        """Force a complete application reset."""
        logger.warning("Forcing application reset")
        return self.model_fleet_manager.trigger_application_reset()

    def can_submit_today(self) -> bool:
        """Check if we can submit alphas today (only once per day)."""
        today = datetime.now().date().isoformat()
        
        if self.last_submission_date == today:
            logger.info(f"Already submitted today ({today}). Skipping submission.")
            return False
        
        logger.info(f"Can submit today. Last submission was: {self.last_submission_date}")
        return True

    # run_alpha_expression_miner removed - no longer needed
    # Online LLM generates high quality alphas, no need for variation mining

    def run_alpha_submitter(self, batch_size: int = 5):
        """Run alpha submitter with daily rate limiting."""
        logger.info("Starting alpha submitter...")

        if not self.can_submit_today():
            return

        try:
            # Run the alpha submitter as a subprocess
            # 增加超时时间：每个 alpha 最多 20 分钟监控 + 30 秒等待，批次间 120 秒
            # 假设 batch_size=3，最多需要 3*(20*60+30) + 2*120 = 约 63 分钟
            result = subprocess.run([
                sys.executable, 'improved_alpha_submitter.py',
                '--batch-size', str(batch_size)
            ], capture_output=True, text=True, timeout=5400)  # 90 分钟超时

            if result.returncode == 0:
                logger.info("Successfully completed alpha submission")
                # Update submission date
                self.last_submission_date = datetime.now().date().isoformat()
                self.save_submission_history()
            else:
                logger.error(f"Alpha submission failed: {result.stderr}")

        except subprocess.TimeoutExpired:
            logger.error("Alpha submission timed out after 90 minutes")
        except Exception as e:
            logger.error(f"Error running alpha submitter: {e}")

    def run_alpha_generator(self, batch_size: int = 5, sleep_time: int = 30):
        """Run the main alpha generator with Ollama."""
        logger.info("Starting alpha generator with Ollama...")
        
        # Get current model from fleet manager
        current_model = self.model_fleet_manager.get_current_model().name
        logger.info(f"Using model: {current_model}")
        
        try:
            # Run the alpha generator as a subprocess
            result = subprocess.run([
                sys.executable, 'alpha_generator_ollama.py',
                '--batch-size', str(batch_size),
                '--sleep-time', str(sleep_time),
                '--ollama-url', self.ollama_url,
                '--ollama-model', current_model,
                '--max-concurrent', str(self.max_concurrent_simulations)
            ], capture_output=True, text=True, timeout=3600)  # 1 hour timeout
            
            if result.returncode == 0:
                logger.info("Alpha generator completed successfully")
            else:
                logger.error(f"Alpha generator failed: {result.stderr}")
                
        except subprocess.TimeoutExpired:
            logger.error("Alpha generator timed out")
        except Exception as e:
            logger.error(f"Error running alpha generator: {e}")

    def start_alpha_generator_continuous(self, batch_size: int = 3, sleep_time: int = 30):
        """Start alpha generator in continuous mode as a background process."""
        logger.info("Starting alpha generator in continuous mode...")

        # Get current model
        if self.use_online_llm and self.llm_client:
            current_model = self.llm_client.get_model_name()
        elif self.model_fleet_manager:
            current_model = self.model_fleet_manager.get_current_model().name
        else:
            current_model = "llama3:8b"
        logger.info(f"Using model: {current_model}")

        try:
            self.generator_process = subprocess.Popen([
                sys.executable, 'alpha_generator_ollama.py',
                '--batch-size', str(batch_size),
                '--sleep-time', str(sleep_time),
                '--ollama-url', self.ollama_url,
                '--ollama-model', current_model,
                '--max-concurrent', str(self.max_concurrent_simulations)
            ])  # 不捕获输出，让子进程继承父进程的 stdout/stderr

            # 添加到子进程跟踪列表
            self._child_processes.append(self.generator_process)
            logger.info(f"Alpha generator started with PID: {self.generator_process.pid}")

        except Exception as e:
            logger.error(f"Error starting alpha generator: {e}")

    # start_alpha_expression_miner_continuous removed - no longer needed

    def restart_all_processes(self):
        """Restart all running processes to prevent stuck jobs."""
        logger.info("🔄 Restarting all processes to prevent stuck jobs...")

        # Stop current processes (不设置 running=False)
        self._stop_subprocesses()

        # Wait a moment for processes to terminate
        time.sleep(5)

        # 确保运行状态为 True
        self.running = True

        # Restart processes
        try:
            # Restart alpha generator
            logger.info("🔄 Restarting alpha generator...")
            self.start_alpha_generator_continuous(batch_size=3, sleep_time=30)

            # Restart VRAM monitoring
            logger.info("🔄 Restarting VRAM monitoring...")
            self.start_vram_monitoring()

            logger.info("✅ All processes restarted successfully")
            self.last_restart_time = time.time()

        except Exception as e:
            logger.error(f"❌ Error during restart: {e}")
            import traceback
            logger.error(traceback.format_exc())

    def _stop_subprocesses(self):
        """停止子进程，但不改变运行状态"""
        logger.info("Stopping subprocesses...")

        # Stop VRAM monitoring
        self.stop_vram_monitoring()

        if self.generator_process:
            logger.info("Terminating alpha generator process...")
            self.generator_process.terminate()
            try:
                self.generator_process.wait(timeout=30)
            except subprocess.TimeoutExpired:
                logger.warning("Force killing alpha generator process...")
                self.generator_process.kill()

        if self.miner_process:
            logger.info("Terminating alpha miner process...")
            self.miner_process.terminate()
            try:
                self.miner_process.wait(timeout=30)
            except subprocess.TimeoutExpired:
                logger.warning("Force killing alpha miner process...")
                self.miner_process.kill()

    def stop_processes(self):
        """Stop all running processes."""
        logger.info("Stopping all processes...")
        self.running = False

        # Stop restart thread
        if self.restart_thread and self.restart_thread.is_alive():
            logger.info("Stopping restart monitoring thread...")

        # 停止子进程
        self._stop_subprocesses()

    def daily_workflow(self):
        """Run the complete daily workflow."""
        logger.info("Starting daily alpha workflow...")
        
        # 1. Run alpha generator for a few hours
        logger.info("Phase 1: Running alpha generator...")
        self.run_alpha_generator(batch_size=3, sleep_time=60)
        
        # 2. Run alpha expression miner on promising alphas
        logger.info("Phase 2: Running alpha expression miner...")
        self.run_alpha_expression_miner()
        
        # 3. Run alpha submitter (once per day)
        logger.info("Phase 3: Running alpha submitter...")
        self.run_alpha_submitter(batch_size=3)
        
        logger.info("Daily workflow completed")

    def continuous_mining(self, mining_interval_hours: int = 6):
        """Run continuous mining with alpha generation only (miner step removed)."""
        logger.info(f"Starting continuous mining...")

        try:
            # Start VRAM monitoring (仅 Ollama 模式)
            if not self.use_online_llm:
                logger.info("Starting VRAM monitoring...")
                self.start_vram_monitoring()
            else:
                logger.info("Using online LLM, skipping VRAM monitoring")

            # Start restart monitoring
            logger.info("Starting restart monitoring...")
            self.start_restart_monitoring()

            # Start alpha generator in continuous mode
            self.start_alpha_generator_continuous(batch_size=3, sleep_time=30)

            # Schedule daily submission at 2 PM
            schedule.every().day.at("14:00").do(self.run_alpha_submitter)

            logger.info("Alpha generator is running (miner step removed - using online LLM generates high quality alphas)")
            logger.info(f"Max concurrent simulations: {self.max_concurrent_simulations}")
            if self.use_online_llm:
                logger.info(f"Using online LLM: {self.llm_client.get_model_name()}")

            while self.running:
                try:
                    # Run pending scheduled tasks
                    schedule.run_pending()

                    # Check if generator process is still running
                    if self.generator_process and self.generator_process.poll() is not None:
                        logger.warning("Alpha generator process stopped, restarting...")
                        self.start_alpha_generator_continuous(batch_size=3, sleep_time=30)

                    # Small delay before next cycle
                    time.sleep(60)

                except KeyboardInterrupt:
                    logger.info("Received interrupt signal, stopping...")
                    break
                except Exception as e:
                    logger.error(f"Error in continuous mining: {e}")
                    time.sleep(300)  # Wait 5 minutes before retrying

        finally:
            self.stop_processes()

def main():
    # 初始化多进程安全日志系统
    setup_mp_logging('INFO')

    parser = argparse.ArgumentParser(description='Alpha Orchestrator - Manage alpha generation and submission')
    parser.add_argument('--credentials', type=str, default='./credential.txt',
                      help='Path to credentials file (default: ./credential.txt)')
    parser.add_argument('--ollama-url', type=str, default='http://localhost:11434',
                      help='Ollama API URL (default: http://localhost:11434)')
    parser.add_argument('--mode', type=str, choices=['daily', 'continuous', 'submitter', 'generator', 'fleet-status', 'fleet-reset', 'fleet-downgrade', 'fleet-reset-app', 'restart', 'select-model'],
                      default='continuous', help='Operation mode (default: continuous)')
    parser.add_argument('--batch-size', type=int, default=None,
                      help='Batch size for operations (default: from config or 3)')
    parser.add_argument('--max-concurrent', type=int, default=None,
                      help='Maximum concurrent simulations (default: from config or 3)')
    parser.add_argument('--restart-interval', type=int, default=30,
                      help='Restart interval in minutes (default: 30)')
    parser.add_argument('--ollama-model', type=str, default=None,
                      help='Ollama model to use (default: from config or llama3:8b)')
    parser.add_argument('--config', type=str, default='config.json',
                      help='Path to config file (default: config.json)')
    parser.add_argument('--select-model', action='store_true',
                      help='启动时交互式选择模型')

    args = parser.parse_args()

    # 模型选择模式
    if args.mode == 'select-model' or args.select_model:
        try:
            from model_selector import main as model_selector_main
            model_selector_main()
        except ImportError:
            logger.error("model_selector 模块未找到")
            print("[错误] 请确保 model_selector.py 存在")
        return 0

    # 加载配置
    config = None
    if CONFIG_AVAILABLE:
        config_manager = get_config_manager(args.config)
        config = config_manager.config

    # 确定参数值（命令行 > 配置文件 > 默认值）
    batch_size = args.batch_size or (config.batch_size if config else 3)
    max_concurrent = args.max_concurrent or (config.max_concurrent if config else 3)
    ollama_model = args.ollama_model or (config.default_model if config else 'llama3:8b')

    # 如果没有指定模型且配置可用，尝试交互式选择
    if not args.ollama_model and not args.select_model:
        try:
            # 检查是否有环境变量指定模型
            env_model = os.environ.get('SELECTED_MODEL')
            if env_model:
                ollama_model = env_model
                logger.info(f"使用环境变量指定的模型: {ollama_model}")
        except:
            pass

    try:
        orchestrator = AlphaOrchestrator(
            args.credentials,
            args.ollama_url,
            config_path=args.config,
            model_override=ollama_model
        )
        orchestrator.max_concurrent_simulations = max_concurrent
        orchestrator.restart_interval = args.restart_interval * 60  # Convert minutes to seconds

        logger.info(f"配置信息:")
        logger.info(f"  - 模型: {ollama_model}")
        logger.info(f"  - 批次大小: {batch_size}")
        logger.info(f"  - 最大并发: {max_concurrent}")

        if args.mode == 'daily':
            orchestrator.daily_workflow()
        elif args.mode == 'continuous':
            orchestrator.continuous_mining()
        elif args.mode == 'submitter':
            orchestrator.run_alpha_submitter(batch_size)
        elif args.mode == 'generator':
            orchestrator.run_alpha_generator(batch_size)
        elif args.mode == 'fleet-status':
            status = orchestrator.get_model_fleet_status()
            print(json.dumps(status, indent=2))
        elif args.mode == 'fleet-reset':
            orchestrator.reset_model_fleet()
            print("Model fleet reset to largest model")
        elif args.mode == 'fleet-downgrade':
            orchestrator.force_model_downgrade()
            print("Model fleet downgraded to next smaller model")
        elif args.mode == 'fleet-reset-app':
            orchestrator.force_application_reset()
            print("Application reset completed - returned to largest model")
        elif args.mode == 'restart':
            orchestrator.restart_all_processes()
            print("Manual restart completed")

    except Exception as e:
        logger.error(f"Fatal error: {e}")
        return 1

    return 0

if __name__ == "__main__":
    exit(main())
