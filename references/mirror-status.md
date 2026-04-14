# Z-Library 镜像探测说明

## 镜像缓存文件

路径：`~/.book-hunter/mirrors.json`

格式：
```json
{
  "valid_mirrors": ["https://z-library.sk", "https://z-lib.id"],
  "checked_at": "2026-04-08T10:00:00Z",
  "ttl_hours": 6
}
```

## 已知镜像列表（截至 2026-04）

| 域名 | 状态 | 备注 |
|------|------|------|
| z-library.sk | 活跃 | 主镜像 |
| z-lib.id | 活跃 | 备用 |
| z-lib.gs | 偶发封锁 | 轮询备用 |
| z-lib.se | 偶发封锁 | 轮询备用 |

> ⚠️ 镜像状态随时变化，若全部 503，清除缓存文件重新探测。

## Anna's Archive 域名

- 主域名：`https://annas-archive.org`
- 备用一：`https://annas-archive.gs`
- 备用二：`https://annas-archive.se`
- Jina 绕过反爬：`https://r.jina.ai/https://annas-archive.org/search?q=<query>`

## Exa 兜底搜索

Web search fallback (optional): Use `exa` CLI or any search tool to find book links

Exa 返回结果是通用搜索，质量不保证，仅作最后兜底。
