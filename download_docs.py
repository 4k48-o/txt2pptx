#!/usr/bin/env python3
"""
下载 manus 提供的所有文档到 manusdoc 文件夹
"""
import os
import re
import urllib.request
import urllib.error
from pathlib import Path

def extract_urls_from_api_md(file_path):
    """从 api.md 文件中提取所有 URL"""
    urls = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            # 提取引号中的 URL
            match = re.search(r'"([^"]+)"', line)
            if match:
                urls.append(match.group(1))
    return urls

def download_document(url, output_dir):
    """下载单个文档"""
    try:
        print(f"正在下载: {url}")
        req = urllib.request.Request(url)
        req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        
        with urllib.request.urlopen(req, timeout=30) as response:
            content = response.read().decode('utf-8')
        
        # 从 URL 中提取相对路径
        # 例如: https://open.manus.ai/docs.md -> docs.md
        # 例如: https://open.manus.ai/docs/quickstart.md -> docs/quickstart.md
        url_path = url.replace('https://open.manus.ai/', '')
        
        # 构建输出文件路径
        output_path = Path(output_dir) / url_path
        
        # 创建必要的目录
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 保存文件
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"✓ 已保存: {output_path}")
        return True
    except Exception as e:
        print(f"✗ 下载失败 {url}: {e}")
        return False

def main():
    # 获取脚本所在目录
    script_dir = Path(__file__).parent
    api_md_path = script_dir / 'manusdoc' / 'api.md'
    output_dir = script_dir / 'manusdoc'
    
    # 提取所有 URL
    urls = extract_urls_from_api_md(api_md_path)
    print(f"找到 {len(urls)} 个文档 URL\n")
    
    # 下载所有文档
    success_count = 0
    for url in urls:
        if download_document(url, output_dir):
            success_count += 1
    
    print(f"\n完成! 成功下载 {success_count}/{len(urls)} 个文档")

if __name__ == '__main__':
    main()
