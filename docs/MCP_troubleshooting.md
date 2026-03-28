# MCP 故障排查指南

**创建时间**: 2026-03-28
**MCP 服务器**: http://82.156.17.205/cnstock/mcp
**状态**: 已验证可用

---

## 一、快速诊断

```python
import sys; sys.path.insert(0, 'stock-assistant/scripts')
from mcp_utils import mcp_health_check, mcp_brief, normalize_symbol

# 1. 健康检查
ok, ms, err = mcp_health_check()
print(f"MCP: {'OK' if ok else 'FAIL'} ({ms:.0f}ms)")

# 2. 测试查询（必须先 normalize）
text = mcp_brief(normalize_symbol('605365'))
print(f"立达信: {'OK' if text and 'No data' not in text else 'EMPTY'}")
```

---

## 二、常见错误

### 1. "No data found for symbol: 605365"

**原因**: 未调用 `normalize_symbol()`

**解决**:
```python
# ❌ 错误
mcp_brief('605365')

# ✅ 正确
from mcp_utils import normalize_symbol
mcp_brief(normalize_symbol('605365'))
```

---

### 2. HTTP 406 Not Acceptable

**原因**: `Accept` 头格式错误

**解决**:
```python
headers = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream"  # 必须 comma-separated
}
```

---

### 3. HTTP 400 Bad Request

**原因**: JSON-RPC 请求格式错误

**解决**:
```python
payload = {
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {"name": "brief", "arguments": {"symbol": "SH605365"}},
    "id": 1
}
```

---

### 4. mcp_full() 返回空

**原因**: 部分股票（如 SH605365）full 数据为空

**解决**: 使用 `mcp_full_safe()` 自动降级到 medium

---

### 5. Unicode docstring SyntaxError

**原因**: 文件开头 docstring 含中文全角括号，在某些 Python 环境解析失败

**解决**: 重写为纯 ASCII 注释

---

## 三、代码规范

所有调用 MCP 的代码必须：

1. **先 normalize**：`mcp_brief(normalize_symbol(code))`
2. **用对的 Accept 头**: `application/json, text/event-stream`
3. **用 mcp_full_safe()**: 查 full 数据时优先使用
4. **处理超时**: 默认 8 秒，health_check 用 5 秒

---

## 四、已知约束

| 约束 | 状态 | 解决方案 |
|------|------|----------|
| MCP full 对部分股票返回空 | 已知 | mcp_full_safe() |
| industry_hot tool 不可用 | 已知 | 降级到 medium 板块数据 |
| MCP URL: http://82.156.17.205 | 稳定 | - |
| 非交易时段 akshare 慢 | 已知 | 用 eastmoney push2 |

---

## 五、测试命令

```bash
# MCP 健康检查
curl -s http://82.156.17.205/cnstock/mcp \
  -X POST -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","method":"tools/list","params":{},"id":1}'

# 检查 MCP URL 是否可访问
curl -s --max-time 5 http://82.156.17.205/ -o /dev/null -w '%{http_code}'
```
