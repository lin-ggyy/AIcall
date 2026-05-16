import logging


class CustomFormatter(logging.Formatter):
    def format(self, record):
        if not hasattr(record, 'ip'):
            record.ip = 'unknown'
        return super().format(record)


log_format = "%(asctime)s - %(ip)s - %(message)s"


class ExcludeThirdPartyFilter(logging.Filter):
    def filter(self, record):
        # 如果记录的logger名字以 "openai" 或 "httpx" 开头，则过滤掉该记录
        if record.name.startswith("openai") or record.name.startswith("httpx"):
            return False
        return True


def setup_logging(log_file: str = "llm_test.log", level=logging.INFO):
    logging.basicConfig(
        filename=log_file,
        level=level,
        format=log_format,
        encoding="GBK"  # 指定日志文件编码为 UTF-8
    )
    # 为所有 handler 设置自定义 Formatter 和过滤器
    for handler in logging.getLogger().handlers:
        handler.setFormatter(CustomFormatter(log_format))
        handler.addFilter(ExcludeThirdPartyFilter())
    return logging.getLogger(__name__)


class CustomAdapter(logging.LoggerAdapter):
    def process(self, msg, kwargs):
        extra = kwargs.get("extra", {})
        ip = extra.get("ip", "unknown")
        kwargs["extra"] = {"ip": ip}
        return msg, kwargs