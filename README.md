一个基于 FastAPI 的轻量级大模型调用服务，提供统一的 API 接口来调用 LLM。

## 项目结构

├── run.py              # FastAPI 主入口，定义 /ai_call 接口
├── ai_request.py       # Pydantic 请求体模型
├── llm_api.py          # LLM API 调用封装
├── logger_config.py    # 日志配置
├── requirements.txt    # 依赖清单
└── venv/               # 虚拟环境（不上传）



## 快速开始

### 1. 克隆项目

```bash
git clone https://github.com/lin-ggyy/AIcall.git
cd AIcall
2. 创建虚拟环境并安装依赖

python -m venv venv
venv\Scripts\activate    # Windows
# source venv/bin/activate  # Mac/Linux
pip install -r requirements.txt
3. 配置 API Key
设置环境变量：


# Windows PowerShell
setx DEEPSEEK_API_KEY "你的key"

# Mac/Linux
export DEEPSEEK_API_KEY="你的key"
默认使用 DeepSeek API，如需更换其他模型，修改 llm_api.py 中的 base_url 和 model。

4. 启动服务

python run.py
服务运行在 http://127.0.0.1:8000

5. 测试接口

curl.exe -X POST http://127.0.0.1:8000/ai_call -H "Content-Type: application/json" -d "{\"prompt\": \"你好\"}"
返回示例：


{"code": 200, "message": "你好！有什么我可以帮忙的吗？"}
接口说明
项目	说明
路径	POST /ai_call
请求体	{"prompt": "你的问题"}
成功返回	{"code": 200, "message": "AI 回复"}
限流	每个 IP 每分钟 5 次
参数缺失	{"code": 500, "message": "缺少提示词参数"}
超限	{"code": 500, "message": "请求太频繁了，请稍后再试"}
技术栈
FastAPI — Web 框架
OpenAI SDK — LLM 调用（兼容协议）
DeepSeek — 大模型
slowapi — 速率限制
Pydantic — 数据校验
uvicorn — ASGI 服务器

