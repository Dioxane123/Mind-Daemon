"""
Task 2: LLM精神状态分析器 - 利用LLM分析性能指标并生成分析报告

功能：
- 收集一段时间内的performance metrics统计数据
- 使用专业的心理分析prompt调用LLM
- 生成结构化的精神状态分析报告
- 支持多种LLM API接口

作者：Mind Daemon Project
"""

import pandas as pd
import numpy as np
import os
import json
import requests
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class MetricsStatistics:
    """指标统计数据"""
    metric_name: str
    mean: float
    std: float
    min_val: float
    max_val: float
    trend: str  # 'increasing', 'decreasing', 'stable'
    latest_value: float
    samples_count: int

@dataclass
class AnalysisPeriod:
    """分析时间段"""
    start_time: str
    end_time: str
    duration_minutes: int
    total_samples: int
    
@dataclass
class LLMAnalysisResult:
    """LLM分析结果"""
    summary: str
    mental_state_assessment: str
    key_insights: List[str]
    recommendations: List[str]
    risk_factors: List[str]
    positive_indicators: List[str]
    confidence_level: str
    analysis_timestamp: str

class LLMAnalyzer:
    """LLM分析器主类"""
    
    def __init__(self, data_dir: str = None, llm_config: Dict[str, Any] = None):
        """
        初始化LLM分析器
        
        Args:
            data_dir: CSV数据目录
            llm_config: LLM配置，包含API endpoint, key等
        """
        if data_dir is None:
            data_dir = os.path.join(os.path.dirname(__file__), 'append_logs')
        
        self.data_dir = data_dir
        self.llm_config = llm_config or {}
        
        # 默认分析时间窗口 (分钟)
        self.default_analysis_window = 30
        
        logger.info(f"LLM分析器初始化完成，数据目录: {self.data_dir}")

    def collect_metrics_statistics(self, window_minutes: int = None) -> tuple[List[MetricsStatistics], AnalysisPeriod]:
        """
        收集指定时间窗口内的指标统计数据
        
        Args:
            window_minutes: 分析时间窗口（分钟），默认30分钟
            
        Returns:
            (统计数据列表, 分析时间段信息)
        """
        if window_minutes is None:
            window_minutes = self.default_analysis_window
            
        try:
            # 加载最新的met数据
            met_files = [f for f in os.listdir(self.data_dir) if f.startswith('met_') and f.endswith('.csv')]
            if not met_files:
                raise FileNotFoundError("未找到met数据文件")
            
            latest_met = sorted(met_files)[-1]
            met_path = os.path.join(self.data_dir, latest_met)
            met_data = pd.read_csv(met_path)
            
            # 转换时间列
            met_data['time'] = pd.to_datetime(met_data['time'])
            
            # 计算时间窗口
            end_time = met_data['time'].max()
            start_time = end_time - timedelta(minutes=window_minutes)
            
            # 筛选时间窗口内的数据
            window_data = met_data[met_data['time'] >= start_time].copy()
            
            if len(window_data) < 2:
                logger.warning("时间窗口内数据点不足，使用全部数据")
                window_data = met_data.copy()
                start_time = met_data['time'].min()
            
            # 定义需要分析的指标列
            metric_columns = ['attention', 'eng', 'exc', 'str', 'rel', 'int']
            available_metrics = [col for col in metric_columns if col in window_data.columns]
            
            # 计算每个指标的统计数据
            statistics = []
            for metric in available_metrics:
                values = window_data[metric].dropna()
                if len(values) == 0:
                    continue
                    
                # 基本统计量
                mean_val = values.mean()
                std_val = values.std()
                min_val = values.min()
                max_val = values.max()
                latest_val = values.iloc[-1]
                
                # 趋势分析（简单的线性回归斜率）
                if len(values) >= 3:
                    x = range(len(values))
                    trend_slope = np.polyfit(x, values, 1)[0]
                    if trend_slope > 0.01:
                        trend = 'increasing'
                    elif trend_slope < -0.01:
                        trend = 'decreasing'
                    else:
                        trend = 'stable'
                else:
                    trend = 'stable'
                
                stat = MetricsStatistics(
                    metric_name=self._translate_metric_name(metric),
                    mean=round(mean_val, 3),
                    std=round(std_val, 3),
                    min_val=round(min_val, 3),
                    max_val=round(max_val, 3),
                    trend=trend,
                    latest_value=round(latest_val, 3),
                    samples_count=len(values)
                )
                statistics.append(stat)
            
            # 分析时间段信息
            period = AnalysisPeriod(
                start_time=start_time.isoformat(),
                end_time=end_time.isoformat(),
                duration_minutes=int((end_time - start_time).total_seconds() / 60),
                total_samples=len(window_data)
            )
            
            logger.info(f"收集了{len(statistics)}个指标的统计数据，时间窗口: {window_minutes}分钟")
            
            return statistics, period
            
        except Exception as e:
            logger.error(f"收集指标统计失败: {e}")
            raise

    def _translate_metric_name(self, metric: str) -> str:
        """翻译指标名称为中文"""
        translations = {
            'attention': '注意力',
            'eng': '参与度',  
            'exc': '兴奋度',
            'str': '压力度',
            'rel': '放松度',
            'int': '兴趣度'
        }
        return translations.get(metric, metric)

    def generate_analysis_prompt(self, statistics: List[MetricsStatistics], 
                               period: AnalysisPeriod) -> str:
        """
        生成专业的心理分析prompt
        
        Args:
            statistics: 指标统计数据
            period: 分析时间段
            
        Returns:
            格式化的prompt字符串
        """
        
        # 构建统计数据摘要
        stats_summary = []
        for stat in statistics:
            trend_desc = {'increasing': '上升', 'decreasing': '下降', 'stable': '稳定'}[stat.trend]
            stats_summary.append(
                f"- {stat.metric_name}: 平均值{stat.mean:.2f}, 当前值{stat.latest_value:.2f}, "
                f"变化范围{stat.min_val:.2f}-{stat.max_val:.2f}, 趋势{trend_desc}"
            )
        
        stats_text = "\n".join(stats_summary)
        
        prompt = f"""你是一位专业的心理学家和神经科学专家，擅长分析脑机接口(BCI)数据来评估人的精神状态。

请基于以下BCI性能指标数据，对用户在过去{period.duration_minutes}分钟的精神状态进行专业分析：

## 数据概览
- 分析时间段: {period.start_time} 至 {period.end_time}
- 总时长: {period.duration_minutes}分钟
- 数据样本数: {period.total_samples}个

## 性能指标统计
{stats_text}

## 分析要求
请从以下几个维度进行深入分析，并提供JSON格式的结构化报告：

1. **整体精神状态评估**: 基于各项指标的综合表现，判断用户当前的主要精神状态
2. **关键洞察**: 识别数据中最重要的模式和异常点  
3. **积极指标**: 指出表现良好的方面
4. **风险因素**: 识别可能需要关注的问题
5. **建议措施**: 基于分析结果提供具体的改善建议
6. **置信度**: 评估分析结论的可靠程度

## 专业背景知识参考：
- 注意力和参与度高通常表示专注状态
- 压力度持续偏高可能表示焦虑或压力过大
- 放松度和压力度应该呈负相关
- 兴趣度反映内在动机水平
- 指标的波动性也很重要，过度波动可能表示不稳定状态

请以专业、客观、有建设性的语调进行分析，避免过度医学化的表述。

输出格式要求：
```json
{{
    "summary": "100-150字的总体状态摘要",
    "mental_state_assessment": "具体的精神状态判断",
    "key_insights": ["洞察1", "洞察2", "洞察3"],
    "recommendations": ["建议1", "建议2", "建议3"],
    "risk_factors": ["风险因素1", "风险因素2"],
    "positive_indicators": ["积极指标1", "积极指标2"],
    "confidence_level": "高/中/低"
}}
```"""

        return prompt

    def call_llm_api(self, prompt: str, llm_type: str = "generic") -> str:
        """
        调用LLM API进行分析
        
        Args:
            prompt: 分析prompt
            llm_type: LLM类型 ("generic", "openai", "minimax", 等)
            
        Returns:
            LLM响应文本
        """
        try:
            if llm_type == "minimax":
                return self._call_minimax_api(prompt)
            elif llm_type == "openai":
                return self._call_openai_api(prompt)
            else:
                # 通用接口或模拟响应
                return self._generate_mock_response(prompt)
                
        except Exception as e:
            logger.error(f"LLM API调用失败: {e}")
            return self._generate_fallback_response()

    def _call_minimax_api(self, prompt: str) -> str:
        """调用MiniMax API"""
        # 这里可以实现MiniMax API的具体调用逻辑
        # 现在先返回模拟响应
        logger.info("调用MiniMax API（当前为模拟模式）")
        return self._generate_mock_response(prompt)
    
    def _call_openai_api(self, prompt: str) -> str:
        """调用OpenAI API"""
        # 这里可以实现OpenAI API的具体调用逻辑  
        logger.info("调用OpenAI API（当前为模拟模式）")
        return self._generate_mock_response(prompt)

    def _generate_mock_response(self, prompt: str) -> str:
        """生成模拟的LLM响应（用于测试）"""
        mock_response = {
            "summary": "用户在过去30分钟内整体表现出相对稳定的精神状态。注意力和参与度维持在中等水平，压力度适中，放松度良好。整体而言，用户处于一个较为平衡的认知状态，具备进行专注性工作的基础条件。",
            "mental_state_assessment": "平衡的认知状态，轻度专注倾向",
            "key_insights": [
                "注意力和参与度指标显示稳定的专注能力",
                "压力度和放松度达到良好的平衡",
                "各项指标变化趋势相对平缓，表示状态稳定"
            ],
            "recommendations": [
                "保持当前的工作节奏，适合进行需要持续注意力的任务",
                "可以考虑安排一些需要深度思考的工作",
                "建议每60-90分钟进行短暂休息以维持状态"
            ],
            "risk_factors": [
                "长时间维持当前状态可能导致疲劳累积",
                "需要关注是否有隐性压力积累的迹象"
            ],
            "positive_indicators": [
                "稳定的注意力水平表示良好的认知控制能力",
                "适中的兴趣度显示内在动机充足"
            ],
            "confidence_level": "中"
        }
        
        return json.dumps(mock_response, ensure_ascii=False, indent=2)

    def _generate_fallback_response(self) -> str:
        """生成备用响应"""
        fallback = {
            "summary": "由于技术原因无法完成详细分析，建议稍后重试或联系技术支持。",
            "mental_state_assessment": "无法确定",
            "key_insights": ["分析服务暂时不可用"],
            "recommendations": ["稍后重试分析", "检查网络连接"],
            "risk_factors": ["分析结果不可用"],
            "positive_indicators": [],
            "confidence_level": "低"
        }
        
        return json.dumps(fallback, ensure_ascii=False, indent=2)

    def parse_llm_response(self, response_text: str) -> LLMAnalysisResult:
        """
        解析LLM响应为结构化结果
        
        Args:
            response_text: LLM原始响应
            
        Returns:
            结构化的分析结果
        """
        try:
            # 尝试解析JSON响应
            if "```json" in response_text:
                # 提取JSON部分
                start = response_text.find("```json") + 7
                end = response_text.find("```", start)
                json_text = response_text[start:end].strip()
            else:
                json_text = response_text.strip()
            
            parsed = json.loads(json_text)
            
            return LLMAnalysisResult(
                summary=parsed.get("summary", ""),
                mental_state_assessment=parsed.get("mental_state_assessment", ""),
                key_insights=parsed.get("key_insights", []),
                recommendations=parsed.get("recommendations", []),
                risk_factors=parsed.get("risk_factors", []),
                positive_indicators=parsed.get("positive_indicators", []),
                confidence_level=parsed.get("confidence_level", "中"),
                analysis_timestamp=datetime.now().isoformat()
            )
            
        except Exception as e:
            logger.error(f"解析LLM响应失败: {e}")
            # 返回默认结果
            return LLMAnalysisResult(
                summary="响应解析失败，无法生成分析报告",
                mental_state_assessment="未知",
                key_insights=["响应格式错误"],
                recommendations=["重新运行分析"],
                risk_factors=["分析结果不可靠"],
                positive_indicators=[],
                confidence_level="低",
                analysis_timestamp=datetime.now().isoformat()
            )

    def analyze_mental_state(self, window_minutes: int = None, 
                           llm_type: str = "generic") -> LLMAnalysisResult:
        """
        执行完整的精神状态分析 (主要入口函数)
        
        Args:
            window_minutes: 分析时间窗口
            llm_type: 使用的LLM类型
            
        Returns:
            LLM分析结果
        """
        try:
            logger.info(f"开始LLM精神状态分析，时间窗口: {window_minutes or self.default_analysis_window}分钟")
            
            # 1. 收集统计数据
            statistics, period = self.collect_metrics_statistics(window_minutes)
            
            # 2. 生成分析prompt
            prompt = self.generate_analysis_prompt(statistics, period)
            
            # 3. 调用LLM API
            response = self.call_llm_api(prompt, llm_type)
            
            # 4. 解析响应
            result = self.parse_llm_response(response)
            
            logger.info(f"LLM分析完成，置信度: {result.confidence_level}")
            
            return result
            
        except Exception as e:
            logger.error(f"LLM分析失败: {e}")
            # 返回错误结果
            return LLMAnalysisResult(
                summary=f"分析过程出现错误: {str(e)}",
                mental_state_assessment="分析失败",
                key_insights=["系统错误"],
                recommendations=["检查系统配置", "稍后重试"],
                risk_factors=["分析服务不稳定"],
                positive_indicators=[],
                confidence_level="低",
                analysis_timestamp=datetime.now().isoformat()
            )

    def save_analysis_report(self, result: LLMAnalysisResult, 
                           filename: str = None) -> str:
        """
        保存分析报告到文件
        
        Args:
            result: 分析结果
            filename: 保存文件名，默认自动生成
            
        Returns:
            保存的文件路径
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"llm_analysis_{timestamp}.json"
        
        filepath = os.path.join(self.data_dir, filename)
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(asdict(result), f, ensure_ascii=False, indent=2)
            
            logger.info(f"分析报告已保存: {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"保存报告失败: {e}")
            raise

def main():
    """测试函数"""
    try:
        # 创建分析器
        analyzer = LLMAnalyzer()
        
        # 执行分析
        result = analyzer.analyze_mental_state(window_minutes=30)
        
        # 显示结果
        print(f"\n=== LLM精神状态分析报告 ===")
        print(f"分析时间: {result.analysis_timestamp}")
        print(f"置信度: {result.confidence_level}")
        print(f"\n总体评估: {result.mental_state_assessment}")
        print(f"\n状态摘要:\n{result.summary}")
        
        print(f"\n关键洞察:")
        for insight in result.key_insights:
            print(f"  • {insight}")
        
        print(f"\n建议措施:")
        for rec in result.recommendations:
            print(f"  • {rec}")
        
        print(f"\n积极指标:")
        for pos in result.positive_indicators:
            print(f"  • {pos}")
        
        if result.risk_factors:
            print(f"\n需要关注的风险:")
            for risk in result.risk_factors:
                print(f"  • {risk}")
        
        # 保存报告
        filepath = analyzer.save_analysis_report(result)
        print(f"\n报告已保存至: {filepath}")
        
    except Exception as e:
        print(f"测试失败: {e}")

if __name__ == "__main__":
    main()