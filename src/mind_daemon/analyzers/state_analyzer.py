"""
Task 1: 状态分析器 - 结合传统方法与BCI指标进行精神状态分析

功能：
- 读取met和pow CSV数据
- 使用传统算法分析EEG频段功率
- 结合performance metrics进行状态判断
- 输出精神状态码

作者：Mind Daemon Project
"""

import pandas as pd
import numpy as np
import os
from typing import Dict, Tuple, List, Optional
from dataclasses import dataclass
from enum import Enum
import logging
import math
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MentalState(Enum):
    """精神状态枚举"""
    FOCUSED = 1          # 专注状态
    RELAXED = 2          # 放松状态  
    EXCITED = 3          # 兴奋状态
    STRESSED = 4         # 压力状态
    DISTRACTED = 5       # 分心状态
    NEUTRAL = 6          # 中性状态
    FATIGUED = 7         # 疲劳状态

@dataclass
class StateAnalysisResult:
    """状态分析结果"""
    state: MentalState
    confidence: float
    details: str
    metrics: Dict[str, float]
    timestamp: str

@dataclass
class BCIMetrics:
    """BCI指标数据结构"""
    # Performance Metrics
    attention: float
    engagement: float
    excitement: float
    stress: float
    relaxation: float
    interest: float
    
    # Power Data (主要电极)
    frontal_left_alpha: float = 0.0    # F3/alpha
    frontal_right_alpha: float = 0.0   # F4/alpha  
    frontal_theta: float = 0.0         # Fz/theta (近似)
    parietal_alpha: float = 0.0        # 顶叶alpha
    frontal_beta: float = 0.0          # 额叶beta

class StateAnalyzer:
    """状态分析器主类"""
    
    def __init__(self, data_dir: str = None):
        """
        初始化状态分析器
        
        Args:
            data_dir: CSV数据文件目录，默认从.env文件读取DATA_PATH
        """
        if data_dir is None:
            # 从环境变量读取数据目录路径
            data_path = os.getenv('DATA_PATH', './data')
            # 如果是相对路径，从当前工作目录解析
            if not os.path.isabs(data_path):
                data_dir = os.path.abspath(data_path)
            else:
                data_dir = data_path
        
        self.data_dir = data_dir
        
        # 确保数据目录存在
        if not os.path.exists(self.data_dir):
            logger.warning(f"数据目录不存在: {self.data_dir}")
        
        # 状态判断阈值 (基于经验设定，可后续调优)
        self.thresholds = {
            'attention_high': 0.7,
            'attention_low': 0.3,
            'engagement_high': 0.7,
            'engagement_low': 0.3,
            'stress_high': 0.7,
            'relaxation_high': 0.7,
            'excitement_high': 0.7,
            'fatigue_theta_beta_ratio': 1.2,
            'engagement_beta_alpha_ratio': 1.8
        }
        
        logger.info(f"状态分析器初始化完成，数据目录: {self.data_dir}")

    def load_latest_data(self) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        加载最新的met和pow数据
        
        Returns:
            (met_data, pow_data): 元组包含两个DataFrame
        """
        try:
            # 检查数据目录是否存在
            if not os.path.exists(self.data_dir):
                raise FileNotFoundError(f"数据目录不存在: {self.data_dir}")
            
            # 找到最新的CSV文件
            met_files = [f for f in os.listdir(self.data_dir) if f.startswith('met_') and f.endswith('.csv')]
            pow_files = [f for f in os.listdir(self.data_dir) if f.startswith('pow_') and f.endswith('.csv')]
            
            if not met_files or not pow_files:
                raise FileNotFoundError(f"在目录 {self.data_dir} 中未找到met或pow数据文件")
            
            # 使用最新文件
            latest_met = sorted(met_files)[-1]
            latest_pow = sorted(pow_files)[-1]
            
            met_path = os.path.join(self.data_dir, latest_met)
            pow_path = os.path.join(self.data_dir, latest_pow)
            
            met_data = pd.read_csv(met_path)
            pow_data = pd.read_csv(pow_path)
            
            logger.info(f"加载数据文件: {latest_met}, {latest_pow}")
            logger.info(f"Met数据: {len(met_data)}行, Pow数据: {len(pow_data)}行")
            
            # 转换时间列
            if 'time' in met_data.columns:
                met_data['time'] = pd.to_datetime(met_data['time'])
            if 'time' in pow_data.columns:
                pow_data['time'] = pd.to_datetime(pow_data['time'])
            
            return met_data, pow_data
            
        except Exception as e:
            logger.error(f"加载数据失败: {e}")
            raise

    def extract_metrics(self, met_data: pd.DataFrame, pow_data: pd.DataFrame, 
                       window_size: int = 5) -> BCIMetrics:
        """
        从数据中提取BCI指标
        
        Args:
            met_data: 性能指标数据
            pow_data: 功率数据
            window_size: 滑动窗口大小（取最近几个数据点的平均值）
            
        Returns:
            BCIMetrics对象
        """
        try:
            # 取最近的数据点进行平均
            recent_met = met_data.tail(window_size)
            recent_pow = pow_data.tail(window_size)
            
            # 提取performance metrics (注意CSV中可能有isActive列)
            attention = recent_met['attention'].mean() if 'attention' in recent_met.columns else 0.5
            engagement = recent_met['eng'].mean() if 'eng' in recent_met.columns else 0.5
            excitement = recent_met['exc'].mean() if 'exc' in recent_met.columns else 0.5
            stress = recent_met['str'].mean() if 'str' in recent_met.columns else 0.5
            relaxation = recent_met['rel'].mean() if 'rel' in recent_met.columns else 0.5
            interest = recent_met['int'].mean() if 'int' in recent_met.columns else 0.5
            
            # 提取关键电极的功率数据
            frontal_left_alpha = 0.0
            frontal_right_alpha = 0.0
            frontal_theta = 0.0
            parietal_alpha = 0.0
            frontal_beta = 0.0
            
            if not recent_pow.empty:
                # F3和F4电极的alpha功率 (FAA计算需要)
                if 'F3/alpha' in recent_pow.columns:
                    frontal_left_alpha = recent_pow['F3/alpha'].mean()
                if 'F4/alpha' in recent_pow.columns:
                    frontal_right_alpha = recent_pow['F4/alpha'].mean()
                
                # 额叶theta功率 (使用F3, F4平均)
                if 'F3/theta' in recent_pow.columns and 'F4/theta' in recent_pow.columns:
                    frontal_theta = (recent_pow['F3/theta'].mean() + recent_pow['F4/theta'].mean()) / 2
                elif 'AF3/theta' in recent_pow.columns:
                    frontal_theta = recent_pow['AF3/theta'].mean()
                    
                # 顶叶alpha (用于参与度计算)
                if 'P7/alpha' in recent_pow.columns and 'P8/alpha' in recent_pow.columns:
                    parietal_alpha = (recent_pow['P7/alpha'].mean() + recent_pow['P8/alpha'].mean()) / 2
                elif 'O1/alpha' in recent_pow.columns:
                    parietal_alpha = recent_pow['O1/alpha'].mean()
                    
                # 额叶beta功率
                if 'F3/betaL' in recent_pow.columns and 'F4/betaL' in recent_pow.columns:
                    frontal_beta = (recent_pow['F3/betaL'].mean() + recent_pow['F4/betaL'].mean()) / 2
                elif 'AF3/betaL' in recent_pow.columns:
                    frontal_beta = recent_pow['AF3/betaL'].mean()
            
            return BCIMetrics(
                attention=attention,
                engagement=engagement,
                excitement=excitement,
                stress=stress,
                relaxation=relaxation,
                interest=interest,
                frontal_left_alpha=frontal_left_alpha,
                frontal_right_alpha=frontal_right_alpha,
                frontal_theta=frontal_theta,
                parietal_alpha=parietal_alpha,
                frontal_beta=frontal_beta
            )
            
        except Exception as e:
            logger.error(f"提取指标失败: {e}")
            # 返回默认值
            return BCIMetrics(
                attention=0.5, engagement=0.5, excitement=0.5,
                stress=0.5, relaxation=0.5, interest=0.5
            )

    def calculate_traditional_indicators(self, metrics: BCIMetrics) -> Dict[str, float]:
        """
        计算传统EEG指标 (基于state_analyse_algo.py中的算法)
        
        Args:
            metrics: BCI指标对象
            
        Returns:
            传统指标字典
        """
        indicators = {}
        
        try:
            # 1. 额叶Alpha不对称性 (FAA) - 抑郁风险指标
            if metrics.frontal_left_alpha > 0 and metrics.frontal_right_alpha > 0:
                faa = math.log(metrics.frontal_right_alpha) - math.log(metrics.frontal_left_alpha)
                indicators['frontal_alpha_asymmetry'] = faa
            else:
                indicators['frontal_alpha_asymmetry'] = 0.0
            
            # 2. 参与度指数 (Beta/Alpha比率)
            if metrics.parietal_alpha > 0:
                engagement_index = metrics.frontal_beta / metrics.parietal_alpha
                indicators['engagement_index'] = engagement_index
            else:
                indicators['engagement_index'] = 1.0
                
            # 3. 疲劳指数 (Theta/Beta比率)
            if metrics.frontal_beta > 0:
                fatigue_index = metrics.frontal_theta / metrics.frontal_beta
                indicators['fatigue_index'] = fatigue_index
            else:
                indicators['fatigue_index'] = 1.0
                
            # 4. 整体arousal水平 (beta + gamma相对功率)
            total_power = metrics.frontal_theta + metrics.frontal_left_alpha + metrics.frontal_beta
            if total_power > 0:
                arousal_level = metrics.frontal_beta / total_power
                indicators['arousal_level'] = arousal_level
            else:
                indicators['arousal_level'] = 0.3
                
        except Exception as e:
            logger.error(f"计算传统指标失败: {e}")
            indicators = {
                'frontal_alpha_asymmetry': 0.0,
                'engagement_index': 1.0,
                'fatigue_index': 1.0,
                'arousal_level': 0.3
            }
        
        return indicators

    def classify_mental_state(self, metrics: BCIMetrics, 
                            traditional_indicators: Dict[str, float]) -> StateAnalysisResult:
        """
        分类精神状态
        
        Args:
            metrics: BCI指标
            traditional_indicators: 传统EEG指标
            
        Returns:
            状态分析结果
        """
        
        # 准备决策所需的指标
        attention = metrics.attention
        engagement = metrics.engagement
        excitement = metrics.excitement
        stress = metrics.stress
        relaxation = metrics.relaxation
        
        fatigue_index = traditional_indicators.get('fatigue_index', 1.0)
        engagement_index = traditional_indicators.get('engagement_index', 1.0)
        faa = traditional_indicators.get('frontal_alpha_asymmetry', 0.0)
        
        # 状态分类逻辑 (层次化决策树)
        state = MentalState.NEUTRAL
        confidence = 0.5
        details = "中性状态"
        
        # 1. 首先检查疲劳状态 (优先级最高)
        if fatigue_index > self.thresholds['fatigue_theta_beta_ratio']:
            state = MentalState.FATIGUED
            confidence = min(0.9, 0.6 + fatigue_index * 0.1)
            details = f"检测到疲劳状态，Theta/Beta比率: {fatigue_index:.2f}"
            
        # 2. 检查压力状态
        elif stress > self.thresholds['stress_high']:
            state = MentalState.STRESSED
            confidence = min(0.9, 0.5 + stress * 0.4)
            details = f"检测到压力状态，压力指数: {stress:.2f}"
            
        # 3. 检查专注状态
        elif (attention > self.thresholds['attention_high'] and 
              engagement > self.thresholds['engagement_high']):
            state = MentalState.FOCUSED
            confidence = min(0.9, 0.4 + (attention + engagement) * 0.25)
            details = f"检测到专注状态，注意力: {attention:.2f}, 参与度: {engagement:.2f}"
            
        # 4. 检查兴奋状态
        elif excitement > self.thresholds['excitement_high']:
            state = MentalState.EXCITED
            confidence = min(0.9, 0.5 + excitement * 0.4)
            details = f"检测到兴奋状态，兴奋度: {excitement:.2f}"
            
        # 5. 检查放松状态
        elif (relaxation > self.thresholds['relaxation_high'] and 
              stress < 0.4):
            state = MentalState.RELAXED
            confidence = min(0.9, 0.5 + relaxation * 0.4)
            details = f"检测到放松状态，放松度: {relaxation:.2f}"
            
        # 6. 检查分心状态
        elif (attention < self.thresholds['attention_low'] and 
              engagement < self.thresholds['engagement_low']):
            state = MentalState.DISTRACTED
            confidence = min(0.9, 0.5 + (1 - attention - engagement) * 0.25)  
            details = f"检测到分心状态，注意力: {attention:.2f}, 参与度: {engagement:.2f}"
            
        # 7. 默认中性状态
        else:
            state = MentalState.NEUTRAL
            confidence = 0.6
            details = "未检测到明显的特定状态，判断为中性状态"
        
        # 结合传统指标进行置信度调整
        if abs(faa) > 0.5:  # FAA异常值提示可能的情绪异常
            confidence *= 0.9
            details += f" (FAA异常: {faa:.2f})"
        
        # 构建详细指标字典
        all_metrics = {
            'attention': attention,
            'engagement': engagement,
            'excitement': excitement,
            'stress': stress,
            'relaxation': relaxation,
            'interest': metrics.interest,
            'faa': faa,
            'engagement_index': engagement_index,
            'fatigue_index': fatigue_index
        }
        
        return StateAnalysisResult(
            state=state,
            confidence=confidence,
            details=details,
            metrics=all_metrics,
            timestamp=pd.Timestamp.now().isoformat()
        )

    def analyze_current_state(self) -> StateAnalysisResult:
        """
        分析当前精神状态 (主要入口函数)
        
        Returns:
            状态分析结果
        """
        try:
            # 1. 加载数据
            met_data, pow_data = self.load_latest_data()
            
            # 2. 提取指标  
            metrics = self.extract_metrics(met_data, pow_data)
            
            # 3. 计算传统指标
            traditional_indicators = self.calculate_traditional_indicators(metrics)
            
            # 4. 分类状态
            result = self.classify_mental_state(metrics, traditional_indicators)
            
            logger.info(f"状态分析完成: {result.state.name} (置信度: {result.confidence:.2f})")
            
            return result
            
        except Exception as e:
            logger.error(f"状态分析失败: {e}")
            # 返回错误状态
            return StateAnalysisResult(
                state=MentalState.NEUTRAL,
                confidence=0.0,
                details=f"分析失败: {str(e)}",
                metrics={},
                timestamp=pd.Timestamp.now().isoformat()
            )

def main():
    """测试函数"""
    try:
        # 创建分析器
        analyzer = StateAnalyzer()
        
        # 分析当前状态
        result = analyzer.analyze_current_state()
        
        print(f"\n=== 精神状态分析结果 ===")
        print(f"状态: {result.state.name} ({result.state.value})")
        print(f"置信度: {result.confidence:.2f}")
        print(f"详情: {result.details}")
        print(f"时间: {result.timestamp}")
        print(f"\n主要指标:")
        for key, value in result.metrics.items():
            print(f"  {key}: {value:.3f}")
            
    except Exception as e:
        print(f"测试失败: {e}")

if __name__ == "__main__":
    main()