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

## 候选镜像列表

镜像状态随时变化，不在文档中承诺“稳定可用”。脚本会按候选列表运行时探测，并把最近一次可用结果缓存 6 小时。

| 域名 | 备注 |
|------|------|
| z-library.sk | 候选镜像 |
| z-library.se | 候选镜像 |
| z-lib.id | 候选镜像 |
| z-lib.fm | 候选镜像 |
| 1lib.dev | 候选镜像 |
| lib-boc.net | 候选镜像 |
| z-library.rs | 候选镜像 |
| z-library.gs | 候选镜像 |

> ⚠️ 镜像状态随时变化，若全部 503，清除缓存文件重新探测。

## Anna's Archive 域名

- 主域名：`https://annas-archive.org`
- 备用一：`https://annas-archive.gs`
- 备用二：`https://annas-archive.se`
- Jina Reader 文本代理：`https://r.jina.ai/https://annas-archive.org/search?q=<query>`

## Exa 兜底搜索

通过 mcporter 调用：`mcporter call exa.web_search_exa "site:z-library OR site:annas-archive <书名>"`

Exa 返回结果是通用搜索，质量不保证，仅作最后兜底。
