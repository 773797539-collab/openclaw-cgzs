html = open('/home/admin/openclaw/workspace/portal/index.html').read()
print(f"当前HTML长度: {len(html)}")
print(f"末尾50字: {html[-50:]}")
