#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
采集 WorldQuant Brain 所有数据字段
API: https://api.worldquantbrain.com/data-fields
"""

import requests
import json
import time
import os
from typing import List, Dict

def fetch_all_data_fields(credentials_file: str = "credential.txt", resume: bool = True) -> List[Dict]:
    """获取所有数据字段"""

    # 加载凭证
    with open(credentials_file, 'r') as f:
        credentials = json.load(f)

    sess = requests.Session()
    sess.auth = (credentials[0], credentials[1])

    # 必须的请求头
    headers = {
        "accept": "application/json;version=2.0",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    sess.headers.update(headers)

    # 先认证
    auth_resp = sess.post('https://api.worldquantbrain.com/authentication', timeout=30)
    if auth_resp.status_code != 201:
        print(f"认证失败: {auth_resp.status_code}")
        return []
    print("认证成功")

    # 断点续传：加载已保存的数据
    all_fields = []
    if resume and os.path.exists("worldquant_data_fields.json"):
        with open("worldquant_data_fields.json", 'r', encoding='utf-8') as f:
            all_fields = json.load(f)
        print(f"从断点恢复，已加载 {len(all_fields)} 个字段")

    # API 参数
    base_url = "https://api.worldquantbrain.com/data-fields"
    params = {
        "delay": 1,
        "instrumentType": "EQUITY",
        "region": "USA",
        "universe": "TOP3000",
        "limit": 50  # API 限制每页最多 50 条
    }

    offset = len(all_fields)  # 从已保存的位置继续
    total_count = None

    while True:
        params["offset"] = offset

        try:
            print(f"正在获取 offset={offset}...")
            resp = sess.get(base_url, params=params, timeout=60)

            if resp.status_code == 429:
                print(f"触发限流，等待 60 秒后重试...")
                time.sleep(60)
                continue

            if resp.status_code != 200:
                print(f"请求失败: {resp.status_code}, {resp.text[:200]}")
                # 保存已获取的数据
                if all_fields:
                    save_fields_to_file(all_fields)
                break

            data = resp.json()

            if total_count is None:
                total_count = data.get("count", 0)
                print(f"总字段数: {total_count}")

            results = data.get("results", [])
            if not results:
                print("没有更多数据")
                break

            all_fields.extend(results)
            print(f"已获取 {len(all_fields)} / {total_count} 个字段")

            # 每 500 条保存一次
            if len(all_fields) % 500 == 0:
                save_fields_to_file(all_fields)
                print(f"已保存检查点")

            # 检查是否已获取全部
            if len(all_fields) >= total_count:
                print("已获取全部字段")
                break

            offset += params["limit"]
            time.sleep(1.5)  # 避免请求过快，API 限流

        except requests.exceptions.Timeout:
            print(f"请求超时，等待后重试...")
            time.sleep(5)
            continue
        except Exception as e:
            if "429" in str(e) or "rate limit" in str(e).lower():
                print(f"触发限流，等待 60 秒后重试...")
                time.sleep(60)
                continue
            print(f"错误: {e}")
            # 保存已获取的数据
            if all_fields:
                save_fields_to_file(all_fields)
            break

    return all_fields


def save_fields_to_file(fields: List[Dict], output_file: str = "worldquant_data_fields.json"):
    """保存字段到文件"""
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(fields, f, ensure_ascii=False, indent=2)
    print(f"已保存 {len(fields)} 个字段到 {output_file}")


def generate_markdown_reference(fields: List[Dict], output_file: str = "worldquant_data_fields_reference.md"):
    """生成 Markdown 格式的字段参考文档"""

    # 按数据集分组
    datasets = {}
    for field in fields:
        dataset_info = field.get("dataset", {})
        dataset_name = dataset_info.get("name", "Unknown")
        dataset_id = dataset_info.get("id", "unknown")

        key = f"{dataset_id}:{dataset_name}"
        if key not in datasets:
            datasets[key] = {
                "id": dataset_id,
                "name": dataset_name,
                "fields": []
            }

        datasets[key]["fields"].append({
            "id": field.get("id"),
            "description": field.get("description", ""),
            "category": field.get("category", {}).get("name", ""),
            "subcategory": field.get("subcategory", {}).get("name", ""),
            "type": field.get("type", ""),
            "coverage": field.get("coverage", 0)
        })

    # 生成 Markdown
    lines = [
        "# WorldQuant Brain 数据字段参考",
        "",
        f"**总计**: {len(fields)} 个字段",
        f"**数据集**: {len(datasets)} 个",
        "",
        "## 数据集分类",
        ""
    ]

    # 按数据集排序
    for key in sorted(datasets.keys()):
        dataset = datasets[key]
        lines.append(f"### {dataset['name']} ({dataset['id']})")
        lines.append(f"字段数: {len(dataset['fields'])}")
        lines.append("")
        lines.append("| 字段 ID | 描述 | 类别 | 类型 | 覆盖率 |")
        lines.append("|---------|------|------|------|--------|")

        for field in sorted(dataset['fields'], key=lambda x: x['id']):
            desc = field['description'][:50] + "..." if len(field['description']) > 50 else field['description']
            lines.append(f"| {field['id']} | {desc} | {field['category']} | {field['type']} | {field['coverage']}% |")

        lines.append("")

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))

    print(f"已生成 Markdown 参考文档: {output_file}")
    print(f"数据集数量: {len(datasets)}")


if __name__ == "__main__":
    print("开始采集 WorldQuant Brain 数据字段...")

    fields = fetch_all_data_fields()

    if fields:
        save_fields_to_file(fields)
        generate_markdown_reference(fields)

        # 统计信息
        datasets = set()
        categories = set()
        for field in fields:
            datasets.add(field.get("dataset", {}).get("name", "Unknown"))
            categories.add(field.get("category", {}).get("name", "Unknown"))

        print(f"\n统计:")
        print(f"- 总字段数: {len(fields)}")
        print(f"- 数据集数: {len(datasets)}")
        print(f"- 类别数: {len(categories)}")