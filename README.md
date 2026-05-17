# AI_call

基于 FastAPI 的轻量级 LLM 调用服务，支持直接对话、RAG 知识库问答、Agent 自主工具调用。

## 项目结构

```
AI_call/
├── run.py              # FastAPI 主入口，定义所有接口
├── agent.py            # Agent 工具调用核心（LLM 自主决策）
├── ai_request.py       # Pydantic 请求体模型
├── llm_api.py          # DeepSeek 对话 API 封装
├── logger_config.py    # 日志配置模块
├── mcp_server.py       # MCP Server（JSON-RPC over stdio）
├── requirements.txt    # 依赖清单
├── documents/          # 知识库文档目录
│   ├── 公司报销制度.txt
│   └── 出差规定.txt
└── rag/                # RAG 检索模块
    ├── __init__.py
    ├── document.py     # 文档加载与切分
    ├── embedding.py    # 文本向量化（硅基流动 BGE）
    └── vector_store.py # ChromaDB 向量存储与检索
```

## 快速开始

### 1. 克隆项目

```bash
git clone https://github.com/lin-ggyy/AIcall.git
cd AIcall
```

### 2. 创建虚拟环境并安装依赖

```bash
python -m venv venv1

# Windows
venv1\Scripts\activate

# Mac / Linux
source venv/bin/activate

pip install -r requirements.txt
```

### 3. 配置 API Key

项目使用两个模型服务，需设置环境变量：

```powershell
# Windows PowerShell（设置后需重启终端生效）
setx DEEPSEEK_API_KEY "sk-你的DeepSeek密钥"
setx SILICONFLOW_API_KEY "sk-你的硅基流动密钥"

# Mac / Linux
export DEEPSEEK_API_KEY="sk-你的DeepSeek密钥"
export SILICONFLOW_API_KEY="sk-你的硅基流动密钥"
```

| 服务 | 用途 | 获取地址 |
|------|------|----------|
| DeepSeek | 对话 / Agent 推理 | platform.deepseek.com |
| 硅基流动 (BGE) | Embedding 向量化 | siliconflow.cn |

### 4. 启动服务

```bash
python run.py
```

服务运行在 `http://127.0.0.1:8000`，启动时自动加载 `documents/` 目录下的文档到向量数据库。

---

## API 接口

### `/ai_call` — 直接对话

直接调用大模型，不加任何检索增强。

```bash
curl -X POST http://127.0.0.1:8000/ai_call \
  -H "Content-Type: application/json" \
  -d '{"prompt": "你好"}'
```

### `/rag_call` — 知识库问答

先从本地文档检索相关内容，再发给 LLM 生成答案，返回答案来源。

```bash
curl -X POST http://127.0.0.1:8000/rag_call \
  -H "Content-Type: application/json" \
  -d '{"prompt": "报销流程是什么"}'
```

返回示例：

```json
{
  "code": 200,
  "message": "根据公司报销制度，报销流程为：员工填写《费用报销单》...",
  "sources": ["公司报销制度\n\n一、报销流程\n..."]
}
```

### `/agent_call` — 智能代理

LLM 自主判断需要调用哪个工具（知识库检索 / 天气查询），工具描述：

| 工具 | 触发场景 |
|------|----------|
| search_knowledge_base | 公司制度、规定、报销等问题 |
| get_weather | 天气、气温相关问题 |

```bash
curl -X POST http://127.0.0.1:8000/agent_call \
  -H "Content-Type: application/json" \
  -d '{"prompt": "广州今天天气怎么样"}'
```

### `/reload` — 文档热重载

新增或修改 `documents/` 目录下文件后，无需重启服务即可生效。

```bash
curl -X POST http://127.0.0.1:8000/reload \
  -H "Content-Type: application/json" \
  -d '{}'
```

### 接口对比

| 接口 | 信息来源 | 智能程度 | 使用场景 |
|------|----------|----------|----------|
| `/ai_call` | LLM 自身知识 | 基础 | 闲聊、通用问题 |
| `/rag_call` | 本地文档 + LLM | 增强 | 查询内部资料 |
| `/agent_call` | 自主选工具 | 最高 | 混合场景，无需手动选择 |

---

## 速率限制

所有接口每个 IP 每分钟限 5 次请求，超限返回：

```json
{"code": 500, "message": "请求太频繁了，请稍后再试"}
```

---

## Agent 工作流程

```
用户提问
    │
    ▼
LLM 判断意图 ──→ 需要查文档？ → 调用 search_knowledge_base
    │               │
    │          需要查天气？ → 调用 get_weather
    │               │
    │          不需要工具？ → 直接回复
    │
    ▼
对工具结果组织语言，返回最终答案
```
## 如何新增 Agent 工具

想让 LLM 学会一个新能力，只需在 `agent.py` 中改三个地方。以天气查询为例：

### 第一步：写工具函数

```python
def get_weather(city: str) -> str:
    """你的工具逻辑，返回结果字符串"""
    # 调用外部 API、查数据库、做计算...
    return f"{city}：晴，28°C"
```

### 第二步：在 TOOLS 列表注册

```python
{
    "type": "function",
    "function": {
        "name": "get_weather",                    # 函数名，LLM 用它来「点名」
        "description": "查询城市实时天气。当用户问到天气、气温时使用。",  # 什么时候用
        "parameters": {
            "type": "object",
            "properties": {
                "city": {
                    "type": "string",
                    "description": "城市名称，如：广州"
                }
            },
            "required": ["city"]                  # 必填参数
        }
    }
}
```

| 字段 | 作用 | 写得好坏的影响 |
|------|------|---------------|
| `name` | LLM 调用时用的标识 | 必须和函数名一致 |
| `description` | LLM 判断什么时候该用这个工具 | 写模糊了 LLM 可能不调用，或者乱调用 |
| `parameters` | 工具需要什么参数 | LLM 根据这个决定传什么值 |

### 第三步：在 execute_tool 添加分支

```python
def execute_tool(name: str, arguments: dict) -> str:
    if name == "search_knowledge_base":
        ...
    elif name == "get_weather":           # ← 新增这个分支
        city = arguments.get("city", "")
        return get_weather(city)
    return f"未知工具: {name}"
```

### 搞定

重启服务后，LLM 自动识别新工具。可以用以下模板继续扩充：

| 想法 | 实现思路 |
|------|----------|
| 查数据库 | 函数里连 MySQL / PostgreSQL |
| 调用内部 API | 函数里发 HTTP 请求到其他服务 |
| 发送邮件 | 函数里调 SMTP |
| 数学计算 | 函数里执行精确计算（LLM 不擅长算数） |
| 搜索网页 | 函数里调搜索引擎 API |


---

## 技术栈

| 组件 | 技术 |
|------|------|
| Web 框架 | FastAPI |
| 大模型对话 | DeepSeek (deepseek-chat) |
| 向量化 | 硅基流动 BAAI/bge-large-zh-v1.5 |
| 向量数据库 | ChromaDB (PersistentClient) |
| 速率限制 | slowapi |
| 数据校验 | Pydantic |
| 服务器 | uvicorn |
| MCP 协议 | mcp (Model Context Protocol) |

---

## 许可证

MIT
