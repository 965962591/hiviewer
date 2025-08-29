# HiViewer 日志系统使用指南

## 概述

HiViewer 使用 Python 标准库 `logging` 模块实现了一套完整的日志系统，支持控制台输出和文件记录，具备日志轮转功能。

## 日志系统特性

- ✅ **双重输出**: 同时支持控制台和文件输出
- ✅ **日志轮转**: 自动管理日志文件大小和数量
- ✅ **可配置**: 通过 JSON 配置文件灵活调整
- ✅ **错误处理**: 具备后备机制，确保日志系统稳定运行
- ✅ **性能监控**: 提供专门的性能记录功能

## 快速开始

### 1. 启用日志系统

在主程序启动时，日志系统会自动初始化：

```python
if __name__ == '__main__':
    # 初始化日志文件
    setup_logging()
    
    # 设置主程序app
    app = QApplication(sys.argv)
    window = HiviewerMainwindow()
    sys.exit(app.exec_())
```

### 2. 基本使用

```python
import logging
from src.common.manager_log import setup_logging, get_logger

# 初始化日志系统
setup_logging()

# 获取日志器
logger = get_logger(__name__)

# 记录不同级别的日志
logging.debug("调试信息")
logging.info("一般信息")
logging.warning("警告信息")
logging.error("错误信息")
logging.critical("严重错误")
```

## 日志级别

| 级别 | 数值 | 说明 |
|------|------|------|
| DEBUG | 10 | 调试信息，开发时使用 |
| INFO | 20 | 一般信息，记录程序运行状态 |
| WARNING | 30 | 警告信息，可恢复的异常 |
| ERROR | 40 | 错误信息，影响功能的错误 |
| CRITICAL | 50 | 严重错误，程序可能崩溃 |

## 配置文件

日志系统通过 `config/log_config.json` 文件进行配置：

```json
{
    "console_level": "DEBUG",           // 控制台日志级别
    "file_level": "INFO",               // 文件日志级别
    "max_file_size": 10485760,          // 最大文件大小（字节）
    "backup_count": 5,                  // 备份文件数量
    "log_format": "%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s",
    "date_format": "%Y-%m-%d %H:%M:%S",
    "enable_console": true,             // 是否启用控制台输出
    "enable_file": true                 // 是否启用文件输出
}
```

## 高级功能

### 1. 性能监控

```python
from src.common.manager_log import log_performance
import time

def process_files(file_list):
    start_time = time.time()
    
    # 处理文件...
    result = len(file_list)
    
    end_time = time.time()
    log_performance("文件处理", start_time, end_time, file_count=len(file_list))
    
    return result
```

### 2. 错误记录

```python
from src.common.manager_log import log_error

try:
    # 可能出错的代码
    result = risky_operation()
except Exception as e:
    log_error("文件处理失败", extra_data={"file_count": len(files)})
    raise
```

### 3. 装饰器使用

```python
from src.common.decorator import log_performance_decorator, error_handler_decorator

@log_performance_decorator("图片处理")
@error_handler_decorator("图片处理失败")
def process_image(image_path):
    # 处理图片的代码
    pass
```

## 日志文件位置

- **主日志文件**: `cache/logs/hiviewer.log`
- **后备日志文件**: `cache/logs/hiviewer_fallback.log`
- **轮转文件**: `cache/logs/hiviewer.log.1`, `hiviewer.log.2`, ...

## 最佳实践

### 1. 日志消息格式

```python
# 好的日志消息
logging.info(f"文件处理成功 [大小：{size}MB] [类型：{file_type}]")
logging.error(f"数据库连接失败 [主机：{host}] [端口：{port}]")

# 避免的日志消息
logging.info("处理完成")  # 信息不够详细
logging.error("出错了")   # 信息不够具体
```

### 2. 异常处理

```python
try:
    # 业务代码
    result = process_data()
except FileNotFoundError as e:
    logging.error(f"文件未找到: {e.filename}", exc_info=True)
except Exception as e:
    logging.error(f"未知错误: {str(e)}", exc_info=True)
```

### 3. 性能监控

```python
import time

def expensive_operation():
    start_time = time.time()
    
    # 耗时操作
    result = do_work()
    
    end_time = time.time()
    logging.info(f"操作完成，耗时：{end_time - start_time:.2f}s")
    
    return result
```

## 故障排除

### 1. 日志文件不生成

- 检查 `cache/logs` 目录是否存在
- 确认程序有写入权限
- 查看控制台是否有错误信息

### 2. 日志级别不生效

- 检查配置文件格式是否正确
- 确认配置文件路径正确
- 重启程序使配置生效

### 3. 日志文件过大

- 调整 `max_file_size` 参数
- 减少 `backup_count` 参数
- 提高 `file_level` 级别

## 示例代码

### 完整的模块示例

```python
import logging
from src.common.manager_log import setup_logging, get_logger, log_performance
import time

# 获取模块日志器
logger = get_logger(__name__)

class ImageProcessor:
    def __init__(self):
        logger.info("图片处理器初始化")
    
    def process_image(self, image_path):
        start_time = time.time()
        
        try:
            logger.debug(f"开始处理图片: {image_path}")
            
            # 处理图片的代码
            result = self._do_process(image_path)
            
            end_time = time.time()
            log_performance("图片处理", start_time, end_time, 
                          file_path=image_path, result=result)
            
            logger.info(f"图片处理成功: {image_path}")
            return result
            
        except Exception as e:
            logger.error(f"图片处理失败: {image_path}", exc_info=True)
            raise
    
    def _do_process(self, image_path):
        # 实际的图片处理逻辑
        pass
```

这个日志系统为 HiViewer 提供了完整的日志记录功能，帮助开发者调试和监控程序运行状态。
