## 精神状态算法:

### **算法一：临床导向的精神状态监测 (基于个人基线偏移)**

**🎯 目标**:
长期、被动地监测用户的EEG模式，识别与抑郁风险相关的、具有统计学意义的偏离。此算法的核心是**与个人健康状态下的基线进行比较**。

**🔬 核心神经科学原理**:

- **额叶Alpha不对称性 (Frontal Alpha Asymmetry, FAA)**: 右侧额叶Alpha功率相对左侧的优势，与消极情绪和回避动机相关，是抑郁的一个核心生物标记物。
- **静息态Theta功率**: 额叶区域Theta波的异常增高，可能与快感缺失和认知迟缓有关。
- **基线偏移理论**: 精神状态的变化表现为关键EEG指标对其个人稳定期均值的持续性偏离。

**💾 所需数据**:

1. `PowerData`: 一个数据结构，包含当前时间窗内，从关键电极计算出的各频段功率值。至少需要：
    - `PowerData.frontal_left.alpha` (例如，F3, F7电极的平均Alpha功率)
    - `PowerData.frontal_right.alpha` (例如，F4, F8电极的平均Alpha功率)
    - `PowerData.frontal_midline.theta` (例如，Fz电极的Theta功率)
2. `BaselineProfile`: 一个预先计算好的数据结构，存储了用户在**健康/稳定期**（例如，经过一周的持续监测和评估）的各项指标的统计数据。
    - `BaselineProfile.faa.mean`, `BaselineProfile.faa.std`
    - `BaselineProfile.theta.mean`, `Baseline_Profile.theta.std`

### **伪代码：`analyzeClinicalState`**

```
// ALGORITHM 1: analyzeClinicalState
// -----------------------------------------------------------------------------

FUNCTION analyzeClinicalState(PowerData, BaselineProfile):
    // --- STEP 1: Calculate current neuro-markers from raw power data ---

    // 使用自然对数来计算FAA，这在文献中是标准做法，可以使数据更接近正态分布
    faa_current = ln(PowerData.frontal_right.alpha) - ln(PowerData.frontal_left.alpha)

    // 获取当前额叶中线Theta功率
    theta_current = PowerData.frontal_midline.theta

    // --- STEP 2: Compare current markers to the personal baseline using Z-score ---
    // Z-score可以告诉我们当前值偏离了基线均值多少个标准差，是一个标准化的异常度量。

    faa_z_score = (faa_current - BaselineProfile.faa.mean) / BaselineProfile.faa.std
    theta_z_score = (theta_current - BaselineProfile.theta.mean) / BaselineProfile.theta.std

    // --- STEP 3: Apply decision logic based on the deviation scores ---
    // 这些阈值是示例，实际应用中需要通过临床研究来精确校准。
    // Z-score > 1.96 表示在统计学上显著 (p < 0.05)。我们使用稍高的阈值来增加鲁棒性。

    DEFINE CRITICAL_THRESHOLD = 2.5   // 极显著偏离
    DEFINE MODERATE_THRESHOLD = 2.0   // 中度显著偏离

    // 创建一个结果对象来存储分析详情
    result = CREATE_OBJECT {
        state: "NOMINAL_STABLE",
        faa_z_score: faa_z_score,
        theta_z_score: theta_z_score,
        details: "No significant deviation from baseline detected."
    }

    // 决策树：优先判断主要指标FAA
    IF faa_z_score > CRITICAL_THRESHOLD THEN
        result.state = "HIGH_DEPRESSIVE_RISK"
        result.details = "Frontal Alpha Asymmetry is critically higher than baseline."
        
        // Theta作为一个次要验证指标
        IF theta_z_score > MODERATE_THRESHOLD THEN
            result.details += " Confirmed by significantly elevated frontal theta power."
        END IF

    ELSE IF faa_z_score > MODERATE_THRESHOLD THEN
        result.state = "MODERATE_DEPRESSIVE_RISK"
        result.details = "Frontal Alpha Asymmetry is moderately higher than baseline."

    END IF
    
    // 如果FAA正常，但Theta异常高，也可能是一个需要关注的信号
    ELSE IF theta_z_score > CRITICAL_THRESHOLD THEN
        result.state = "ANOMALOUS_THETA_ACTIVITY"
        result.details = "FAA is stable, but frontal theta power is critically elevated. May indicate anhedonia or cognitive slowing."
    END IF

    // --- STEP 4: Return the structured result ---
    RETURN result

END FUNCTION
```


### **算法二：通用的即时认知状态检测**

**🎯 目标**:
根据当前的EEG信号，实时判断用户正处于疲劳、放松、还是兴奋/专注等常见状态。此算法更侧重于即时性和通用性。

**🔬 核心神经科学原理**:

- **Alpha/Beta 功率的拮抗作用**: 放松状态下Alpha波占优，而专注/兴奋状态下Beta波占优。它们的比率是衡量“参与度”的经典指标。
- **Theta/Beta 比率**: 困倦/疲劳时Theta波会上升，而警觉的Beta波会下降，该比率是衡量疲劳度的有效指标。
- **Alpha抑制 (Alpha Suppression)**: 从事认知任务时，相关脑区（尤其是顶叶和枕叶）的Alpha波功率会显著下降。

**💾 所需数据**:

- `PowerData`: 数据结构，包含关键电极的功率值。
    - `PowerData.frontal.beta`, `PowerData.frontal.theta`
    - `PowerData.parietal.alpha` (顶叶Pz或其周围电极的Alpha功率，这是Alpha抑制的敏感区域)

### **伪代码：`analyzeGeneralCognitiveState`**

```jsx
// -----------------------------------------------------------------------------
// ALGORITHM 2: analyzeGeneralCognitiveState
// -----------------------------------------------------------------------------

FUNCTION analyzeGeneralCognitiveState(PowerData):
    // --- STEP 1: Define thresholds ---
    // 这些是示例阈值。理想情况下，它们应该通过一个简短的个人校准任务来确定。
    // （例如，记录1分钟睁眼和1分钟闭眼的数据来确定Alpha的动态范围）
    
    DEFINE ENGAGEMENT_THRESH_HIGH = 1.8     // Beta/Alpha比率，高参与度
    DEFINE ENGAGEMENT_THRESH_LOW = 0.6      // Beta/Alpha比率，低参与度/放松
    DEFINE FATIGUE_THRESH_HIGH = 1.2        // Theta/Beta比率，高疲劳度

    // --- STEP 2: Calculate key state ratios ---

    // 参与度指数：反映了大脑从放松到活跃的转换。
    // 使用额叶Beta（思考）和顶叶Alpha（放松）进行计算，非常经典。
    engagement_index = PowerData.frontal.beta / PowerData.parietal.alpha

    // 疲劳/困倦指数：反映警觉性的下降。
    fatigue_index = PowerData.frontal.theta / PowerData.frontal.beta

    // --- STEP 3: Hierarchical decision logic for state classification ---
    // 使用一个层级结构，优先判断最明确或最需要关注的状态（如疲劳）。

    result = CREATE_OBJECT {
        state: "NEUTRAL",
        engagement_index: engagement_index,
        fatigue_index: fatigue_index
    }

    // **最高优先级：判断是否疲劳**
    IF fatigue_index > FATIGUE_THRESH_HIGH THEN
        result.state = "FATIGUE_DROWSINESS"
        RETURN result
    END IF

    // **次高优先级：判断是否高度参与/兴奋**
    IF engagement_index > ENGAGEMENT_THRESH_HIGH THEN
        result.state = "HIGH_ENGAGEMENT_EXCITEMENT"
        // 此处可以加入更精细的判断，例如检查Gamma波来区分“焦虑的兴奋”和“高效的专注”
        RETURN result
    END IF

    // **再次之：判断是否放松**
    IF engagement_index < ENGAGEMENT_THRESH_LOW THEN
        result.state = "RELAXED_IDLE"
        RETURN result
    END IF

    // **默认状态**：如果以上条件都不满足，则为中性状态
    // `result.state` 保持为 "NEUTRAL"
    RETURN result

END FUNCTION
```

### **关键的实践考量**

- **基线的重要性**: 第一个算法的成败**完全取决于**基线数据的质量。必须在用户情绪稳定、经临床确认的时期采集，并且数据量要足够大以获得可靠的均值和标准差。
- **个体差异**: 第二个算法中的阈值（如1.8, 0.6）对不同的人来说差异巨大。一个人的“高度专注”可能是另一个人的“普通状态”。因此，一个快速的**个性化校准**流程是让这类算法变得实用的关键。
- **时间动态**: 这些伪代码分析的是一个时间窗的数据。一个更鲁棒的系统需要考虑**状态的持续性**。例如，只有当`analyzeClinicalState`连续多个小时返回“DEPRESSIVE_RISK”时，才真正认为是一个需要关注的事件。
- **上下文信息**: 算法不知道用户正在做什么。一个“放松”的EEG信号在用户冥想时是正常的，但在用户开车时则极其危险。高级系统需要融合上下文信息（如时间、活动日志、手机使用情况）来做出更智能的判断。