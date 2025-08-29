# -*- coding: utf-8 -*-
import os
import sys
import logging
from pathlib import Path
from logging.handlers import RotatingFileHandler
import json

"""设置根目录"""
# 通过当前py文件来定位项目主入口路径，向上找两层父文件夹
if True:
    BASE_PATH = Path(__file__).parent.parent.parent
# 通过主函数hiviewer.py文件来定位项目主入口路径
if False:
    BASE_PATH = Path(sys.argv[0]).parent
    

"""
设置日志区域开始线
------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
需要导入下面两个python内置库:
import logging
from logging.handlers import RotatingFileHandler

相关使用方法：

1. **DEBUG**（调试信息）：
    logging.debug("正在尝试连接数据库...")
    # 适用场景：
    # - 记录程序执行流程
    # - 关键变量值跟踪
    # - 方法进入/退出日志
    # 生产环境应关闭DEBUG级别


2. **INFO**（运行状态信息）：
    logging.info(f"成功加载用户配置：{user_id}")
    # 适用场景：
    # - 重要业务操作记录
    # - 系统状态变更
    # - 成功执行的正常流程
    

3. **WARNING**（预期内异常）：
    logging.warning("缓存未命中，回退到默认配置")
    # 适用场景：
    # - 可恢复的异常情况
    # - 非关键路径的失败操作
    # - 降级处理情况

4. ERROR（严重错误）：
    try:
        # 可能出错的代码
    except Exception as e:
        logging.error("数据库连接失败", exc_info=True)
    # 适用场景：
    # - 关键操作失败
    # - 不可恢复的异常
    # - 影响核心功能的错误

最佳实践建议：


1. **性能监控**：
    start = time.time()
    # 业务操作
    logging.info(f"操作完成，耗时：{time.time()-start:.2f}s")
    
# 好的日志：
logging.info(f"文件处理成功 [大小：{size}MB] [类型：{file_type}]")

# 通过配置文件动态调整
logging.getLogger().setLevel(logging.DEBUG if DEBUG else logging.INFO)

设置日志区域结束线
------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
"""

def load_log_config():
    """加载日志配置文件"""
    config_path = BASE_PATH / "config" / "log_config.json"
    default_config = {
        "console_level": "DEBUG",
        "file_level": "INFO", 
        "max_file_size": 10485760,  # 10MB
        "backup_count": 5,
        "log_format": "%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s",
        "date_format": "%Y-%m-%d %H:%M:%S",
        "enable_console": True,
        "enable_file": True
    }
    
    try:
        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                # 合并默认配置
                for key, value in default_config.items():
                    if key not in config:
                        config[key] = value
                return config
        else:
            # 创建默认配置文件
            config_dir = config_path.parent
            config_dir.mkdir(parents=True, exist_ok=True)
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, indent=4, ensure_ascii=False)
            return default_config
    except Exception as e:
        print(f"加载日志配置失败: {e}, 使用默认配置")
        return default_config

def setup_logging():
    """设置日志系统"""
    try:
        # 加载配置
        config = load_log_config()
        
        # 创建日志目录
        log_dir = BASE_PATH / "cache" / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # 获取日志级别
        level_map = {
            'DEBUG': logging.DEBUG,
            'INFO': logging.INFO,
            'WARNING': logging.WARNING,
            'ERROR': logging.ERROR,
            'CRITICAL': logging.CRITICAL
        }
        
        console_level = level_map.get(config['console_level'], logging.DEBUG)
        file_level = level_map.get(config['file_level'], logging.INFO)
        
        # 创建格式化器
        formatter = logging.Formatter(
            fmt=config['log_format'], 
            datefmt=config['date_format']
        )

        # 获取主日志器
        main_logger = logging.getLogger()
        main_logger.setLevel(logging.DEBUG)
        
        # 清除现有的处理器
        for handler in main_logger.handlers[:]:
            main_logger.removeHandler(handler)

        # 控制台处理器
        if config['enable_console']:
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            console_handler.setLevel(console_level)
            main_logger.addHandler(console_handler)

        # 文件处理器（带轮转功能）
        if config['enable_file']:
            file_handler = RotatingFileHandler(
                filename=log_dir / "hiviewer.log",
                maxBytes=config['max_file_size'],
                backupCount=config['backup_count'],
                encoding="utf-8"
            )
            file_handler.setFormatter(formatter)
            file_handler.setLevel(file_level)
            main_logger.addHandler(file_handler)

        # 记录日志系统启动信息
        logging.info("=" * 65)
        logging.info("HiViewer 日志系统初始化成功")
        logging.info(f"日志文件路径: {log_dir / 'hiviewer.log'}")
        logging.info(f"控制台日志级别: {config['console_level']}")
        logging.info(f"文件日志级别: {config['file_level']}")
        logging.info(f"最大文件大小: {config['max_file_size'] / 1024 / 1024:.1f}MB")
        logging.info(f"备份文件数量: {config['backup_count']}")
        logging.info("=" * 65)
        
    except Exception as e:
        print(f"[setup_logging]--日志系统初始化失败: {e}")
        # 使用最基本的日志配置作为后备
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler(BASE_PATH / "cache" / "logs" / "hiviewer_fallback.log", encoding='utf-8')
            ]
        )
        logging.error(f"日志系统初始化失败，使用后备配置: {e}")

def get_logger(name=None):
    """获取指定名称的日志器"""
    return logging.getLogger(name)

def log_function_call(func_name, *args, **kwargs):
    """记录函数调用"""
    logging.debug(f"函数调用: {func_name}(args={args}, kwargs={kwargs})")

def log_function_result(func_name, result, execution_time=None):
    """记录函数执行结果"""
    if execution_time is not None:
        logging.debug(f"函数完成: {func_name}() -> {result} (耗时: {execution_time:.3f}s)")
    else:
        logging.debug(f"函数完成: {func_name}() -> {result}")

def log_error(error_msg, exc_info=True, extra_data=None):
    """记录错误信息"""
    if extra_data:
        logging.error(f"{error_msg} | 额外数据: {extra_data}", exc_info=exc_info)
    else:
        logging.error(error_msg, exc_info=exc_info)

def log_performance(operation, start_time, end_time, **kwargs):
    """记录性能信息"""
    duration = end_time - start_time
    extra_info = " | ".join([f"{k}={v}" for k, v in kwargs.items()])
    if extra_info:
        logging.info(f"性能记录: {operation} | 耗时: {duration:.3f}s | {extra_info}")
    else:
        logging.info(f"性能记录: {operation} | 耗时: {duration:.3f}s")



