#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
知识抽取器 - 使用 LLM 从知识库提取结构化知识链

功能:
1. 读取知识库文件夹中的所有内容
2. 使用 LLM (复用项目已有的 LLMClient) 提取结构化知识
3. 整合零散知识点形成知识链
4. 输出结构化的知识图谱

知识链结构:
- 基础概念层: Alpha 基本原理、数据类型、操作符
- 技术方法层: 模拟设置、优化技巧、相关性控制
- 实践经验层: 成功案例、失败教训、最佳实践
- 高级策略层: 组合策略、风险控制、长期优化
"""

import os
import json
import argparse
import sys
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path

# 添加 naive-ollama 目录到路径，以便导入 LLMClient
_naive_ollama_path = os.path.join(os.path.dirname(__file__), '..', 'generation_one', 'naive-ollama')
if os.path.exists(_naive_ollama_path):
    sys.path.insert(0, os.path.abspath(_naive_ollama_path))

# 使用统一日志配置
try:
    from logging_config import get_logger
    logger = get_logger(__name__)
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

# 复用项目已有的 LLMClient
try:
    from llm_client import LLMClient
    LLM_CLIENT_AVAILABLE = True
except ImportError:
    LLM_CLIENT_AVAILABLE = False
    logger.warning("LLMClient 不可用，知识抽取功能将受限")


class KnowledgeExtractor:
    """知识抽取器 - 从知识库提取结构化知识链"""

    # 知识库路径（与 fetchers 同级）
    KNOWLEDGE_BASE_PATH = os.path.join(
        os.path.dirname(__file__),
        '..',
        'knowledge_base'
    )

    # 知识链输出文件
    KNOWLEDGE_CHAIN_FILE = "knowledge_chain.json"

    def __init__(self,
                 knowledge_base_path: str = None,
                 config_path: str = "config.json"):
        """
        初始化知识抽取器

        Args:
            knowledge_base_path: 知识库路径
            config_path: 配置文件路径（用于初始化 LLMClient）
        """
        self.knowledge_base_path = knowledge_base_path or self.KNOWLEDGE_BASE_PATH
        self.config_path = config_path
        self.llm_client = None

        # 确保知识库目录存在
        os.makedirs(self.knowledge_base_path, exist_ok=True)

        # 初始化 LLM 客户端（复用项目已有的 LLMClient）
        self._init_llm_client()

    def _init_llm_client(self):
        """初始化 LLM 客户端（复用项目已有的 LLMClient）"""
        if not LLM_CLIENT_AVAILABLE:
            logger.warning("LLMClient 不可用，无法进行知识抽取")
            return

        try:
            self.llm_client = LLMClient(config_path=self.config_path)
            provider = self.llm_client.get_provider()
            model = self.llm_client.get_model_name()
            logger.info(f"LLM 客户端初始化成功: {provider} / {model}")
        except Exception as e:
            logger.error(f"LLM 客户端初始化失败: {e}")
            self.llm_client = None

    def read_knowledge_base(self) -> Dict[str, str]:
        """读取知识库中的所有文件内容

        Returns:
            文件名到内容的映射
        """
        knowledge_contents = {}

        # 排除的大文件列表
        excluded_files = ['worldquant_data_fields_reference.md']  # 太大，会导致 API 错误

        # 遍历知识库目录
        for file_path in Path(self.knowledge_base_path).glob('*'):
            if file_path.is_file() and not file_path.name.startswith('.'):
                # 跳过排除的文件
                if file_path.name in excluded_files:
                    logger.info(f"跳过大文件: {file_path.name}")
                    continue

                try:
                    # 根据文件类型读取
                    if file_path.suffix in ['.md', '.txt']:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                    elif file_path.suffix == '.json':
                        with open(file_path, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            # JSON 文件转换为可读文本
                            content = self._json_to_text(data, file_path.name)
                    else:
                        continue

                    if content.strip():
                        knowledge_contents[file_path.name] = content
                        logger.info(f"读取知识文件: {file_path.name} ({len(content)} 字符)")

                except Exception as e:
                    logger.warning(f"读取文件失败: {file_path.name} - {e}")

        return knowledge_contents

    def _json_to_text(self, data: dict, filename: str) -> str:
        """将 JSON 数据转换为可读文本

        Args:
            data: JSON 数据
            filename: 文件名（用于推断数据类型）

        Returns:
            可读文本描述
        """
        text_parts = []

        if 'data_fields' in filename or 'fields' in data:
            # 数据字段文件
            if isinstance(data, list):
                fields = data
            elif 'fields' in data:
                fields = data['fields']
            else:
                fields = data.get('results', [])

            text_parts.append(f"数据字段列表 (共 {len(fields)} 个字段):\n")
            for field in fields[:50]:  # 只展示前50个避免过长
                if isinstance(field, dict):
                    field_id = field.get('id', 'unknown')
                    field_type = field.get('type', 'unknown')
                    field_desc = field.get('description', '')
                    text_parts.append(f"- {field_id} ({field_type}): {field_desc[:100] if field_desc else '无描述'}")

            if len(fields) > 50:
                text_parts.append(f"\n... 还有 {len(fields) - 50} 个字段")

        elif 'operators' in filename or 'operators' in data:
            # 操作符文件
            operators = data.get('operators', data) if isinstance(data, dict) else data
            text_parts.append(f"操作符列表:\n")
            for op in operators[:30]:
                if isinstance(op, dict):
                    op_name = op.get('name', op.get('id', 'unknown'))
                    op_desc = op.get('description', '')
                    text_parts.append(f"- {op_name}: {op_desc[:100] if op_desc else '无描述'}")
                else:
                    text_parts.append(f"- {op}")

        elif 'knowledge' in filename or 'community' in filename:
            # 知识文件
            if isinstance(data, dict):
                for key, value in data.items():
                    text_parts.append(f"\n## {key}\n{value}")
            else:
                text_parts.append(json.dumps(data, ensure_ascii=False, indent=2))

        else:
            # 其他 JSON 文件
            text_parts.append(json.dumps(data, ensure_ascii=False, indent=2)[:2000])

        return '\n'.join(text_parts)

    def extract_knowledge_chain(self, knowledge_contents: Dict[str, str]) -> Dict:
        """使用 LLM 提取知识链

        Args:
            knowledge_contents: 知识库内容映射

        Returns:
            结构化的知识链
        """
        if not self.llm_client:
            logger.error("LLM 客户端未初始化")
            return {'error': 'LLM 客户端未初始化'}

        if not knowledge_contents:
            logger.warning("知识库内容为空")
            return {'error': '知识库内容为空'}

        # 构建提示词
        prompt = self._build_extraction_prompt(knowledge_contents)

        # 调用 LLM
        try:
            response = self._call_llm(prompt)
            knowledge_chain = self._parse_llm_response(response)
            return knowledge_chain
        except Exception as e:
            logger.error(f"LLM 调用失败: {e}")
            return {'error': str(e)}

    def _build_extraction_prompt(self, knowledge_contents: Dict[str, str]) -> str:
        """构建知识提取提示词

        Args:
            knowledge_contents: 知识库内容

        Returns:
            提示词
        """
        # 拼接所有知识内容
        all_content = "\n\n".join([
            f"=== {filename} ===\n{content}"
            for filename, content in knowledge_contents.items()
        ])

        prompt = f"""你是一个 WorldQuant Alpha 专家，请从以下知识库内容中提取结构化的知识链。

知识库内容:
{all_content}

请按照以下知识链结构进行整理和归纳:

## 第一层: 基础概念
- Alpha 基本原理和定义
- 数据类型分类（矩阵数据、向量数据）
- 核心操作符及其功能

## 第二层: 技术方法
- 模拟设置最佳实践（region, universe, decay, neutralization）
- Alpha 表达式构建技巧
- 相关性控制方法

## 第三层: 实践经验
- 成功 Alpha 的特征和模式
- 常见失败原因和教训
- 优化迭代策略

## 第四层: 高级策略
- 组合策略和复合 Alpha
- 长期表现维护
- 风险控制和稳定性

请以 JSON 格式输出，结构如下:
{{
    "knowledge_chain": {{
        "basic_concepts": [
            {{"concept": "...", "description": "...", "source": "..."}}
        ],
        "technical_methods": [
            {{"method": "...", "description": "...", "best_practice": "...", "source": "..."}}
        ],
        "practical_experience": [
            {{"experience": "...", "lesson": "...", "source": "..."}}
        ],
        "advanced_strategies": [
            {{"strategy": "...", "description": "...", "conditions": "...", "source": "..."}}
        ]
    }},
    "key_insights": ["...", "..."],
    "recommended_patterns": ["...", "..."]
}}

注意:
1. 每个知识点必须标注来源（source 字段）
2. 描述要具体，避免泛泛而谈
3. 从零散内容中提炼系统性知识
4. 识别重复内容并合并
5. 补充隐含的知识关联
"""

        return prompt

    def _call_llm(self, prompt: str) -> str:
        """调用 LLM（使用项目已有的 LLMClient）

        Args:
            prompt: 提示词

        Returns:
            LLM 响应
        """
        logger.info(f"调用 LLM: {self.llm_client.get_provider()} / {self.llm_client.get_model_name()}")

        system_prompt = "你是 WorldQuant Alpha 专家，专注于量化投资策略研究。"

        try:
            response = self.llm_client.generate(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.3,
                max_tokens=4096,  # 合理的输出长度
                timeout=300  # 知识抽取可能需要较长时间
            )
            return response
        except Exception as e:
            logger.error(f"LLM 调用失败: {e}")
            raise

    def _parse_llm_response(self, response: str) -> Dict:
        """解析 LLM 响应

        Args:
            response: LLM 响应文本

        Returns:
            解析后的知识链字典
        """
        # 尝试提取 JSON
        try:
            # 查找 JSON 块
            json_start = response.find('{')
            json_end = response.rfind('}') + 1

            if json_start >= 0 and json_end > json_start:
                json_str = response[json_start:json_end]
                knowledge_chain = json.loads(json_str)
                return knowledge_chain
            else:
                # 没有找到 JSON，返回原始文本
                return {
                    'raw_response': response,
                    'knowledge_chain': {
                        'basic_concepts': [],
                        'technical_methods': [],
                        'practical_experience': [],
                        'advanced_strategies': []
                    }
                }
        except json.JSONDecodeError as e:
            logger.warning(f"JSON 解析失败: {e}")
            return {
                'raw_response': response,
                'parse_error': str(e),
                'knowledge_chain': {
                    'basic_concepts': [],
                    'technical_methods': [],
                    'practical_experience': [],
                    'advanced_strategies': []
                }
            }

    def save_knowledge_chain(self, knowledge_chain: Dict) -> str:
        """保存知识链

        Args:
            knowledge_chain: 知识链数据

        Returns:
            保存的文件路径
        """
        output_path = os.path.join(self.knowledge_base_path, self.KNOWLEDGE_CHAIN_FILE)

        # 添加元数据
        knowledge_chain['metadata'] = {
            'created_at': datetime.now().isoformat(),
            'llm_provider': self.llm_client.get_provider() if self.llm_client else 'unknown',
            'model': self.llm_client.get_model_name() if self.llm_client else 'unknown',
            'source_files': list(self.read_knowledge_base().keys())
        }

        # 保存
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(knowledge_chain, f, ensure_ascii=False, indent=2)

        logger.info(f"知识链已保存: {output_path}")
        return output_path

    def load_knowledge_chain(self) -> Dict:
        """加载已有的知识链

        Returns:
            知识链数据
        """
        output_path = os.path.join(self.knowledge_base_path, self.KNOWLEDGE_CHAIN_FILE)

        if os.path.exists(output_path):
            with open(output_path, 'r', encoding='utf-8') as f:
                return json.load(f)

        return {}

    def update_knowledge_chain(self, new_knowledge: Dict) -> Dict:
        """更新知识链（增量更新，使用 LLM 进行智能合并）

        Args:
            new_knowledge: 新的知识内容

        Returns:
            更新后的知识链
        """
        existing_chain = self.load_knowledge_chain()

        if not existing_chain:
            return new_knowledge

        if not self.llm_client:
            logger.warning("LLM 客户端不可用，使用简单合并")
            return self._simple_merge(existing_chain, new_knowledge)

        # 使用 LLM 进行智能合并
        logger.info("使用 LLM 进行知识链智能合并...")

        prompt = self._build_merge_prompt(existing_chain, new_knowledge)

        try:
            response = self._call_llm(prompt)
            merged_chain = self._parse_llm_response(response)

            # 确保结构完整
            if 'knowledge_chain' not in merged_chain:
                merged_chain = {'knowledge_chain': merged_chain}

            return merged_chain
        except Exception as e:
            logger.error(f"LLM 合并失败: {e}, 使用简单合并")
            return self._simple_merge(existing_chain, new_knowledge)

    def _simple_merge(self, existing_chain: Dict, new_knowledge: Dict) -> Dict:
        """简单合并（当 LLM 不可用时的备用方案）"""
        merged_chain = existing_chain.get('knowledge_chain', {})

        for layer in ['basic_concepts', 'technical_methods', 'practical_experience', 'advanced_strategies']:
            existing_items = merged_chain.get(layer, [])
            new_items = new_knowledge.get('knowledge_chain', {}).get(layer, [])
            merged_chain[layer] = existing_items + new_items

        merged_chain['key_insights'] = list(set(
            existing_chain.get('key_insights', []) + new_knowledge.get('key_insights', [])
        ))
        merged_chain['recommended_patterns'] = list(set(
            existing_chain.get('recommended_patterns', []) + new_knowledge.get('recommended_patterns', [])
        ))

        return {'knowledge_chain': merged_chain}

    def _build_merge_prompt(self, existing_chain: Dict, new_knowledge: Dict) -> str:
        """构建知识合并提示词"""
        existing_json = json.dumps(existing_chain, ensure_ascii=False, indent=2)
        new_json = json.dumps(new_knowledge, ensure_ascii=False, indent=2)

        prompt = f"""你是一个知识管理专家，请将以下两个知识链进行智能合并。

要求：
1. 识别语义相似的知识点，只保留一个更完整/更准确的版本
2. 合互补的知识点，保留双方有价值的内容
3. 去除重复或冗余的内容
4. 保持知识链的四层结构：basic_concepts, technical_methods, practical_experience, advanced_strategies
5. 合并 key_insights 和 recommended_patterns，去除重复

已有知识链：
{existing_json}

新知识链：
{new_json}

请输出合并后的完整知识链 JSON，结构保持不变：
{{
    "knowledge_chain": {{
        "basic_concepts": [...],
        "technical_methods": [...],
        "practical_experience": [...],
        "advanced_strategies": [...]
    }},
    "key_insights": [...],
    "recommended_patterns": [...]
}}
"""
        return prompt

    def _is_similar_knowledge(self, item1: Dict, item2: Dict) -> bool:
        """判断两个知识点是否相似（使用 LLM 进行语义判断）

        Args:
            item1: 知识点1
            item2: 知识点2

        Returns:
            是否相似
        """
        if not self.llm_client:
            # LLM 不可用时，使用简单的关键词匹配作为备用
            return self._simple_similarity_check(item1, item2)

        # 提取知识点文本
        text1 = self._extract_knowledge_text(item1)
        text2 = self._extract_knowledge_text(item2)

        if not text1 or not text2:
            return False

        prompt = f"""判断以下两个知识点是否语义相似或重复。

知识点1: {text1}

知识点2: {text2}

请只回答 "是" 或 "否"，不要有其他内容。如果两个知识点表达相同或非常相似的含义，回答"是"；否则回答"否"。
"""

        try:
            response = self._call_llm(prompt)
            return "是" in response.strip()
        except Exception as e:
            logger.warning(f"LLM 相似度判断失败: {e}")
            return self._simple_similarity_check(item1, item2)

    def _extract_knowledge_text(self, item: Dict) -> str:
        """提取知识点的文本描述"""
        key_fields = ['concept', 'method', 'experience', 'strategy', 'description']
        texts = []
        for field in key_fields:
            if field in item and item[field]:
                texts.append(f"{field}: {item[field]}")
        return "; ".join(texts)

    def _simple_similarity_check(self, item1: Dict, item2: Dict) -> bool:
        """简单的相似度检查（备用方案）"""
        key_fields = ['concept', 'method', 'experience', 'strategy']

        for field in key_fields:
            if field in item1 and field in item2:
                text1 = item1.get(field, '').lower()
                text2 = item2.get(field, '').lower()

                words1 = set(text1.split())
                words2 = set(text2.split())
                overlap = len(words1 & words2) / max(len(words1), len(words2), 1)

                if overlap > 0.6:
                    return True

        return False

    def generate_prompt_enhancement(self) -> Dict:
        """从知识链生成提示词增强内容（使用 LLM 进行智能提取）

        Returns:
            提示词增强配置
        """
        knowledge_chain = self.load_knowledge_chain()

        if not knowledge_chain:
            return {}

        if not self.llm_client:
            logger.warning("LLM 客户端不可用，使用简单提取")
            return self._simple_extract_enhancement(knowledge_chain)

        logger.info("使用 LLM 生成提示词增强配置...")

        # 使用 LLM 智能提取和归纳
        prompt = self._build_enhancement_prompt(knowledge_chain)

        try:
            response = self._call_llm(prompt)
            enhancement = self._parse_llm_response(response)

            # 确保结构完整
            if 'core_patterns' not in enhancement:
                enhancement = {
                    'core_patterns': enhancement.get('core_patterns', []),
                    'random_elements': enhancement.get('random_elements', []),
                    'quality_rules': enhancement.get('quality_rules', [])
                }

            return enhancement
        except Exception as e:
            logger.error(f"LLM 增强提取失败: {e}")
            return self._simple_extract_enhancement(knowledge_chain)

    def _build_enhancement_prompt(self, knowledge_chain: Dict) -> str:
        """构建提示词增强提取的提示词"""
        chain_json = json.dumps(knowledge_chain, ensure_ascii=False, indent=2)

        prompt = f"""你是一个 Alpha 生成专家，请从以下知识链中提取用于 Alpha 生成的提示词增强配置。

知识链：
{chain_json}

请提取并输出以下三类内容：

1. core_patterns（核心骨架模式）: Alpha 生成的核心模式和固定结构，确保基本质量
2. random_elements（随机探索元素）: 可变的操作符、参数、策略组合，增加多样性
3. quality_rules（质量门规则）: 验证和过滤规则，确保输出质量

输出 JSON 格式：
{{
    "core_patterns": [
        {{"pattern": "模式描述", "description": "详细说明", "priority": "high/medium/low"}}
    ],
    "random_elements": [
        {{"element": "元素名称", "options": ["选项1", "选项2"], "weight": 0.0-1.0}}
    ],
    "quality_rules": [
        {{"rule": "规则描述", "reason": "原因", "severity": "critical/warning/info"}}
    ]
}}
"""
        return prompt

    def _simple_extract_enhancement(self, knowledge_chain: Dict) -> Dict:
        """简单提取增强配置（备用方案）"""
        enhancement = {
            'core_patterns': [],
            'random_elements': [],
            'quality_rules': []
        }

        chain = knowledge_chain.get('knowledge_chain', {})

        for concept in chain.get('basic_concepts', []):
            enhancement['core_patterns'].append({
                'pattern': concept.get('concept', ''),
                'description': concept.get('description', '')
            })

        for method in chain.get('technical_methods', []):
            enhancement['random_elements'].append({
                'element': method.get('method', ''),
                'best_practice': method.get('best_practice', '')
            })

        for experience in chain.get('practical_experience', []):
            lesson = experience.get('lesson', '')
            if lesson:
                enhancement['quality_rules'].append({
                    'rule': lesson,
                    'source': experience.get('source', '')
                })

        for insight in knowledge_chain.get('key_insights', []):
            enhancement['quality_rules'].append({
                'rule': insight,
                'source': 'key_insight'
            })

        return enhancement

    def run(self, force: bool = False) -> Dict:
        """运行完整的知识提取流程

        Args:
            force: 是否强制重新提取

        Returns:
            知识链数据
        """
        # 检查是否已有知识链
        existing_chain = self.load_knowledge_chain()

        if existing_chain and not force:
            logger.info("已有知识链，使用增量更新")
            # 读取新内容
            new_contents = self.read_knowledge_base()
            # 提取新知识
            new_knowledge = self.extract_knowledge_chain(new_contents)
            # 合并
            knowledge_chain = self.update_knowledge_chain(new_knowledge)
        else:
            logger.info("开始完整知识提取")
            # 读取所有内容
            knowledge_contents = self.read_knowledge_base()
            # 提取知识链
            knowledge_chain = self.extract_knowledge_chain(knowledge_contents)

        # 保存
        self.save_knowledge_chain(knowledge_chain)

        # 统计
        chain = knowledge_chain.get('knowledge_chain', {})
        stats = {
            'basic_concepts': len(chain.get('basic_concepts', [])),
            'technical_methods': len(chain.get('technical_methods', [])),
            'practical_experience': len(chain.get('practical_experience', [])),
            'advanced_strategies': len(chain.get('advanced_strategies', [])),
            'key_insights': len(knowledge_chain.get('key_insights', [])),
            'recommended_patterns': len(knowledge_chain.get('recommended_patterns', []))
        }

        logger.info(f"知识链统计: {stats}")

        return knowledge_chain


def main():
    """命令行入口"""
    parser = argparse.ArgumentParser(description='知识抽取器 - 从知识库提取结构化知识链')
    parser.add_argument('--config', '-c', type=str, default='config.json',
                       help='配置文件路径')
    parser.add_argument('--knowledge-base', '-b', type=str, help='知识库路径')
    parser.add_argument('--force', '-f', action='store_true', help='强制重新提取')
    parser.add_argument('--generate-enhancement', '-e', action='store_true',
                       help='生成提示词增强配置')

    args = parser.parse_args()

    extractor = KnowledgeExtractor(
        knowledge_base_path=args.knowledge_base,
        config_path=args.config
    )

    if args.generate_enhancement:
        enhancement = extractor.generate_prompt_enhancement()
        print(json.dumps(enhancement, ensure_ascii=False, indent=2))
        return

    # 运行知识提取
    knowledge_chain = extractor.run(force=args.force)

    # 输出摘要
    print("\n知识链提取完成:")
    chain = knowledge_chain.get('knowledge_chain', {})
    print(f"  基础概念: {len(chain.get('basic_concepts', []))} 条")
    print(f"  技术方法: {len(chain.get('technical_methods', []))} 条")
    print(f"  实践经验: {len(chain.get('practical_experience', []))} 条")
    print(f"  高级策略: {len(chain.get('advanced_strategies', []))} 条")
    print(f"  关键洞察: {len(knowledge_chain.get('key_insights', []))} 条")


if __name__ == "__main__":
    main()