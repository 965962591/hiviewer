# -*- coding: utf-8 -*-
import os
import sys
import logging
from pathlib import Path
from logging.handlers import RotatingFileHandler

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

def setup_logging():
    # 创建日志目录
    log_dir = BASE_PATH / "cache" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # 基础配置
    log_format = "%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"
    formatter = logging.Formatter(fmt=log_format, datefmt=date_format)

    # 控制台处理器（开发环境使用）
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.DEBUG)  # 开发时设为DEBUG，生产环境可改为INFO

    # 文件处理器（带轮转功能）
    file_handler = RotatingFileHandler(
        filename=log_dir / "hiviewer.log",
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.INFO)

    # 主日志器配置
    main_logger = logging.getLogger()
    main_logger.setLevel(logging.DEBUG)
    main_logger.addHandler(console_handler)
    main_logger.addHandler(file_handler)



