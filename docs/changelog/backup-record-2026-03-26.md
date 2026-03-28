# 备份记录 - 2026-03-26

## 备份执行

**时间**: 2026-03-26 02:40 GMT+8
**备份文件**: /home/admin/2026-03-25T18-40-25.004Z-openclaw-backup.tar.gz
**工作区备份副本**: /home/admin/openclaw/workspace/backups/2026-03-25T18-40-25.004Z-openclaw-backup.tar.gz

### 备份内容
- state: ~/.openclaw（配置、凭证、session）
- workspace: ~/openclaw/workspace（工作区）

### 验证结果
- ✅ Archive OK
- ✅ 4304 entries scanned
- ✅ 2 assets verified

---

## 备份策略（当前）

| 项目 | 说明 |
|------|------|
| 备份位置 | /home/admin/openclaw/workspace/backups/ |
| 命名规则 | {timestamp}-openclaw-backup.tar.gz |
| 保留策略 | 待定（建议至少保留3份） |
| 验证方式 | openclaw backup verify |

---

## 回滚说明

如需恢复：
```bash
# 查看备份内容
tar -tzf /home/admin/openclaw/workspace/backups/2026-03-25T18-40-25.004Z-openclaw-backup.tar.gz

# 恢复完整备份
openclaw backup restore /home/admin/openclaw/workspace/backups/2026-03-25T18-40-25.004Z-openclaw-backup.tar.gz

# 或手动解压
tar -xzf /home/admin/openclaw/workspace/backups/2026-03-25T18-40-25.004Z-openclaw-backup.tar.gz -C ~
```
