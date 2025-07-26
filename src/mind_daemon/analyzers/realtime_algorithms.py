"""
实时算法分析器 - 基于algorithms.py的实现

实现两个核心算法：
1. 临床导向的精神状态监测 (基于个人基线偏移)
2. 通用的即时认知状态检测

作者：Mind Daemon Project
"""

import math
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from collections import deque
import numpy as np

logger = logging.getLogger(__name__)

@dataclass
class PowerData:
    """功率数据结构"""
    # 前额叶区域
    frontal_left_alpha: float = 0.0    # F3, F7 alpha
    frontal_right_alpha: float = 0.0   # F4, F8 alpha
    frontal_midline_theta: float = 0.0 # 前额中线 theta
    frontal_beta: float = 0.0          # 前额 beta
    frontal_theta: float = 0.0         # 前额 theta
    
    # 顶叶区域
    parietal_alpha: float = 0.0        # 顶叶 alpha (用于参与度计算)

@dataclass
class BaselineProfile:
    """基线数据配置"""
    faa_mean: float = 0.0
    faa_std: float = 1.0
    theta_mean: float = 1.0
    theta_std: float = 0.3

@dataclass
class ClinicalAnalysisResult:
    """临床分析结果"""
    state: str
    faa_z_score: float
    theta_z_score: float
    faa_current: float
    theta_current: float
    details: str

@dataclass
class CognitiveAnalysisResult:
    """认知状态分析结果"""
    state: str
    engagement_index: float
    fatigue_index: float
    details: str

class RealtimeAlgorithms:
    """实时算法分析器"""
    
    def __init__(self):
        # 算法阈值配置
        self.CRITICAL_THRESHOLD = 2.5
        self.MODERATE_THRESHOLD = 2.0
        self.ENGAGEMENT_THRESH_HIGH = 1.8
        self.ENGAGEMENT_THRESH_LOW = 0.6
        self.FATIGUE_THRESH_HIGH = 1.2
        
        # 基线配置（实际应用中应该从用户数据中学习）
        self.baseline_profile = BaselineProfile()
        
        # 历史数据存储（用于动态基线更新）
        self.faa_history = deque(maxlen=1000)
        self.theta_history = deque(maxlen=1000)
        
    def extract_power_data_from_pow(self, pow_data: List[float], pow_labels: List[str]) -> PowerData:
        """从POW数据中提取算法所需的功率数据"""
        try:
            # 创建标签到索引的映射
            label_to_idx = {label: i for i, label in enumerate(pow_labels)}
            
            power_data = PowerData()
            
            # 提取前额叶左侧alpha (F3, F7)
            f3_alpha = pow_data[label_to_idx.get('F3/alpha', 0)] if 'F3/alpha' in label_to_idx else 0.0
            f7_alpha = pow_data[label_to_idx.get('F7/alpha', 0)] if 'F7/alpha' in label_to_idx else 0.0
            power_data.frontal_left_alpha = (f3_alpha + f7_alpha) / 2.0
            
            # 提取前额叶右侧alpha (F4, F8)
            f4_alpha = pow_data[label_to_idx.get('F4/alpha', 0)] if 'F4/alpha' in label_to_idx else 0.0
            f8_alpha = pow_data[label_to_idx.get('F8/alpha', 0)] if 'F8/alpha' in label_to_idx else 0.0
            power_data.frontal_right_alpha = (f4_alpha + f8_alpha) / 2.0
            
            # 提取前额中线theta (AF3, AF4附近)
            af3_theta = pow_data[label_to_idx.get('AF3/theta', 0)] if 'AF3/theta' in label_to_idx else 0.0
            af4_theta = pow_data[label_to_idx.get('AF4/theta', 0)] if 'AF4/theta' in label_to_idx else 0.0
            power_data.frontal_midline_theta = (af3_theta + af4_theta) / 2.0
            
            # 提取前额beta和theta
            f3_beta = pow_data[label_to_idx.get('F3/betaL', 0)] if 'F3/betaL' in label_to_idx else 0.0
            f4_beta = pow_data[label_to_idx.get('F4/betaL', 0)] if 'F4/betaL' in label_to_idx else 0.0
            power_data.frontal_beta = (f3_beta + f4_beta) / 2.0
            
            f3_theta = pow_data[label_to_idx.get('F3/theta', 0)] if 'F3/theta' in label_to_idx else 0.0
            f4_theta = pow_data[label_to_idx.get('F4/theta', 0)] if 'F4/theta' in label_to_idx else 0.0
            power_data.frontal_theta = (f3_theta + f4_theta) / 2.0
            
            # 提取顶叶alpha (使用P7, P8)
            p7_alpha = pow_data[label_to_idx.get('P7/alpha', 0)] if 'P7/alpha' in label_to_idx else 0.0
            p8_alpha = pow_data[label_to_idx.get('P8/alpha', 0)] if 'P8/alpha' in label_to_idx else 0.0
            power_data.parietal_alpha = (p7_alpha + p8_alpha) / 2.0
            
            return power_data
            
        except Exception as e:
            logger.error(f"提取功率数据失败: {e}")
            return PowerData()
    
    def analyze_clinical_state(self, power_data: PowerData) -> ClinicalAnalysisResult:
        """
        算法一：临床导向的精神状态监测 (基于个人基线偏移)
        """
        try:
            # STEP 1: 计算当前神经标记
            # 使用自然对数计算FAA（额叶Alpha不对称性）
            if power_data.frontal_left_alpha > 0 and power_data.frontal_right_alpha > 0:
                faa_current = math.log(power_data.frontal_right_alpha) - math.log(power_data.frontal_left_alpha)
            else:
                faa_current = 0.0
            
            theta_current = power_data.frontal_midline_theta
            
            # 添加到历史数据（用于动态基线更新）
            self.faa_history.append(faa_current)
            self.theta_history.append(theta_current)
            
            # STEP 2: 与个人基线比较计算Z-score
            faa_z_score = (faa_current - self.baseline_profile.faa_mean) / self.baseline_profile.faa_std
            theta_z_score = (theta_current - self.baseline_profile.theta_mean) / self.baseline_profile.theta_std
            
            # STEP 3: 应用决策逻辑
            state = "NOMINAL_STABLE"
            details = "No significant deviation from baseline detected."
            
            if faa_z_score > self.CRITICAL_THRESHOLD:
                state = "HIGH_DEPRESSIVE_RISK"
                details = "Frontal Alpha Asymmetry is critically higher than baseline."
                
                if theta_z_score > self.MODERATE_THRESHOLD:
                    details += " Confirmed by significantly elevated frontal theta power."
                    
            elif faa_z_score > self.MODERATE_THRESHOLD:
                state = "MODERATE_DEPRESSIVE_RISK"
                details = "Frontal Alpha Asymmetry is moderately higher than baseline."
                
            elif theta_z_score > self.CRITICAL_THRESHOLD:
                state = "ANOMALOUS_THETA_ACTIVITY"
                details = "FAA is stable, but frontal theta power is critically elevated. May indicate anhedonia or cognitive slowing."
            
            return ClinicalAnalysisResult(
                state=state,
                faa_z_score=faa_z_score,
                theta_z_score=theta_z_score,
                faa_current=faa_current,
                theta_current=theta_current,
                details=details
            )
            
        except Exception as e:
            logger.error(f"临床状态分析失败: {e}")
            return ClinicalAnalysisResult(
                state="ERROR",
                faa_z_score=0.0,
                theta_z_score=0.0,
                faa_current=0.0,
                theta_current=0.0,
                details=f"Analysis failed: {str(e)}"
            )
    
    def analyze_general_cognitive_state(self, power_data: PowerData) -> CognitiveAnalysisResult:
        """
        算法二：通用的即时认知状态检测
        """
        try:
            # STEP 1: 计算关键状态比率
            # 参与度指数：反映从放松到活跃的转换
            if power_data.parietal_alpha > 0:
                engagement_index = power_data.frontal_beta / power_data.parietal_alpha
            else:
                engagement_index = 0.0
            
            # 疲劳/困倦指数：反映警觉性下降
            if power_data.frontal_beta > 0:
                fatigue_index = power_data.frontal_theta / power_data.frontal_beta
            else:
                fatigue_index = 0.0
            
            # STEP 2: 层级决策逻辑
            state = "NEUTRAL"
            details = "Balanced cognitive state."
            
            # 最高优先级：判断疲劳
            if fatigue_index > self.FATIGUE_THRESH_HIGH:
                state = "FATIGUE_DROWSINESS"
                details = f"High fatigue detected (index: {fatigue_index:.2f}). Consider taking a break."
                
            # 次高优先级：判断高度参与/兴奋
            elif engagement_index > self.ENGAGEMENT_THRESH_HIGH:
                state = "HIGH_ENGAGEMENT_EXCITEMENT"
                details = f"High engagement detected (index: {engagement_index:.2f}). User is actively focused."
                
            # 再次之：判断放松
            elif engagement_index < self.ENGAGEMENT_THRESH_LOW:
                state = "RELAXED_IDLE"
                details = f"Relaxed state detected (index: {engagement_index:.2f}). User is in a calm state."
            
            return CognitiveAnalysisResult(
                state=state,
                engagement_index=engagement_index,
                fatigue_index=fatigue_index,
                details=details
            )
            
        except Exception as e:
            logger.error(f"认知状态分析失败: {e}")
            return CognitiveAnalysisResult(
                state="ERROR",
                engagement_index=0.0,
                fatigue_index=0.0,
                details=f"Analysis failed: {str(e)}"
            )
    
    def update_baseline_profile(self):
        """动态更新基线配置（基于历史数据）"""
        try:
            if len(self.faa_history) > 100:  # 需要足够的历史数据
                faa_array = np.array(list(self.faa_history))
                self.baseline_profile.faa_mean = np.mean(faa_array)
                self.baseline_profile.faa_std = max(np.std(faa_array), 0.1)  # 防止标准差过小
                
            if len(self.theta_history) > 100:
                theta_array = np.array(list(self.theta_history))
                self.baseline_profile.theta_mean = np.mean(theta_array)
                self.baseline_profile.theta_std = max(np.std(theta_array), 0.1)
                
            logger.debug(f"基线已更新: FAA({self.baseline_profile.faa_mean:.3f}±{self.baseline_profile.faa_std:.3f}), "
                        f"Theta({self.baseline_profile.theta_mean:.3f}±{self.baseline_profile.theta_std:.3f})")
                        
        except Exception as e:
            logger.error(f"基线更新失败: {e}")
    
    def get_algorithm_analysis(self, pow_data: List[float], pow_labels: List[str]) -> Dict[str, Any]:
        """
        获取完整的算法分析结果
        """
        try:
            # 提取功率数据
            power_data = self.extract_power_data_from_pow(pow_data, pow_labels)
            
            # 执行两个算法
            clinical_result = self.analyze_clinical_state(power_data)
            cognitive_result = self.analyze_general_cognitive_state(power_data)
            
            # 定期更新基线（每100次分析更新一次）
            if len(self.faa_history) % 100 == 0:
                self.update_baseline_profile()
            
            return {
                'clinical_analysis': {
                    'state': clinical_result.state,
                    'faa_z_score': round(clinical_result.faa_z_score, 3),
                    'theta_z_score': round(clinical_result.theta_z_score, 3),
                    'faa_current': round(clinical_result.faa_current, 3),
                    'theta_current': round(clinical_result.theta_current, 3),
                    'details': clinical_result.details
                },
                'cognitive_analysis': {
                    'state': cognitive_result.state,
                    'engagement_index': round(cognitive_result.engagement_index, 3),
                    'fatigue_index': round(cognitive_result.fatigue_index, 3),
                    'details': cognitive_result.details
                },
                'power_data': {
                    'frontal_left_alpha': round(power_data.frontal_left_alpha, 3),
                    'frontal_right_alpha': round(power_data.frontal_right_alpha, 3),
                    'frontal_beta': round(power_data.frontal_beta, 3),
                    'frontal_theta': round(power_data.frontal_theta, 3),
                    'parietal_alpha': round(power_data.parietal_alpha, 3)
                },
                'baseline_profile': {
                    'faa_mean': round(self.baseline_profile.faa_mean, 3),
                    'faa_std': round(self.baseline_profile.faa_std, 3),
                    'theta_mean': round(self.baseline_profile.theta_mean, 3),
                    'theta_std': round(self.baseline_profile.theta_std, 3)
                }
            }
            
        except Exception as e:
            logger.error(f"算法分析失败: {e}")
            return {
                'error': str(e),
                'clinical_analysis': {'state': 'ERROR'},
                'cognitive_analysis': {'state': 'ERROR'}
            }

# 全局算法分析器实例
_algorithm_analyzer: Optional[RealtimeAlgorithms] = None

def get_algorithm_analyzer() -> RealtimeAlgorithms:
    """获取全局算法分析器实例"""
    global _algorithm_analyzer
    if _algorithm_analyzer is None:
        _algorithm_analyzer = RealtimeAlgorithms()
    return _algorithm_analyzer