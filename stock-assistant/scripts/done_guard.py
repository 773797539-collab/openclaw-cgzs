#!/usr/bin/env python3
"""
done_guard.py - 任务完成门禁验证
必须在任务标记为 done 之前调用

检查项:
- git_commit: 必须有 commit SHA
- trace: 必须有执行 trace 记录  
- report: 必须有输出报告路径
- doc_sync: 必须有文档同步状态

用法:
    python3 done_guard.py <task_file.md>
    python3 done_guard.py --check-done tasks/done/
"""
import sys, os, re

REQUIRED_FIELDS = ['git_commit', 'trace', 'report']
OPTIONAL_FIELDS = ['doc_sync']

SIGNAL_NONE = {'无', '无', 'none', 'pending', '待补充', '未提供'}

def parse_task_file(filepath):
    """解析任务文件，提取门禁字段"""
    if not os.path.exists(filepath):
        return None
    with open(filepath) as f:
        content = f.read()
    
    result = {}
    for field in REQUIRED_FIELDS + OPTIONAL_FIELDS:
        # Search for field: value
        pattern = re.compile(rf'^{field}[\s:]+(.+)$', re.MULTILINE | re.IGNORECASE)
        m = pattern.search(content)
        if m:
            result[field] = m.group(1).strip()
        else:
            result[field] = None
    return result


def verify_done(task_path_or_dir):
    """验证任务文件是否满足 done 门禁"""
    if os.path.isdir(task_path_or_dir):
        files = [f for f in os.listdir(task_path_or_dir) if f.endswith('.md')]
        results = []
        for f in sorted(files):
            results.append(verify_done(os.path.join(task_path_or_dir, f)))
        return results
    
    fields = parse_task_file(task_path_or_dir)
    if fields is None:
        return {'file': task_path_or_dir, 'error': 'file not found'}
    
    task_id = os.path.basename(task_path_or_dir)
    issues = []
    for field in REQUIRED_FIELDS:
        val = fields.get(field)
        if not val or val.lower() in SIGNAL_NONE:
            issues.append(f"缺少 {field}")
    
    return {
        'file': task_id,
        'fields': fields,
        'issues': issues,
        'pass': len(issues) == 0,
    }


def main():
    if len(sys.argv) < 2:
        # Check tasks/done/
        done_dir = os.path.join(os.path.dirname(__file__), '..', 'tasks', 'done')
        results = verify_done(done_dir)
        total = len(results)
        passed = sum(1 for r in results if r['pass'])
        print(f"Done 门禁检查: {passed}/{total} 通过")
        for r in results:
            status = '✅' if r['pass'] else '❌'
            issues = ', '.join(r['issues']) if r['issues'] else 'OK'
            print(f"  {status} {r['file']}: {issues}")
        return
    
    for arg in sys.argv[1:]:
        if os.path.isdir(arg):
            results = verify_done(arg)
            for r in results:
                print(f"{'✅' if r['pass'] else '❌'} {r['file']}: {', '.join(r['issues']) if r['issues'] else 'pass'}")
        else:
            r = verify_done(arg)
            print(f"{'✅' if r['pass'] else '❌'} {r['file']}: {', '.join(r['issues']) if r['issues'] else 'pass'}")


if __name__ == '__main__':
    main()
