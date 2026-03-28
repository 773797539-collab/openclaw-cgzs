# Backups 目录

**最后更新**: 2026-03-28 17:19

## 备份策略

| 项目 | 策略 |
|------|------|
| 保留数量 | 最多 3 个 |
| 保留时间 | 最新 1 个 + 每周日清理 |
| 触发时间 | 每天 03:00（cron） |
| 备份内容 | 全量 workspace 打包 |

## 当前备份

| 文件 | 大小 | 日期 |
|------|------|------|
| 2026-03-25T18-49-19.487Z-openclaw-backup.tar.gz | 287MB | 2026-03-25 02:49 |

## 手动清理

```bash
# 查看大小
du -sh /home/admin/openclaw/workspace/backups/

# 保留最新 3 个
ls -lt /home/admin/openclaw/workspace/backups/*.tar.gz | tail -n +4 | xargs rm -f
```
