// Dashboard JavaScript

class MindDaemonDashboard {
    constructor() {
        this.currentTab = 'basic';
        this.trendsChart = null;
        this.stateHistoryChart = null;
        this.algorithmTrendsChart = null; // 算法指标趋势图表
        this.socket = null;
        this.stateHistory = []; // 存储状态历史
        this.algorithmHistory = []; // 存储算法数据历史
        this.init();
    }

    init() {
        this.updateDateTime();
        this.setupEventListeners();
        this.loadSampleData();
        this.initChart();
        this.initStateHistoryChart();
        this.initAlgorithmTrendsChart(); // 初始化算法趋势图表
        this.connectSocket();
        
        // Update datetime every second
        setInterval(() => this.updateDateTime(), 1000);
    }

    setupEventListeners() {
        // Tab switching is handled by global functions
        // Additional event listeners can be added here
    }

    connectSocket() {
        // Connect to WebSocket server (需要后端支持WebSocket)
        // 注意：原始的socket_interface.py使用TCP socket，需要修改为WebSocket
        try {
            this.socket = new WebSocket('ws://localhost:8889'); // 使用不同端口避免冲突
            
            this.socket.onopen = () => {
                console.log('WebSocket连接已建立');
            };
            
            this.socket.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    this.updateBasicDataFromSocket(data);
                } catch (error) {
                    console.error('解析WebSocket数据错误:', error);
                }
            };
            
            // this.socket.onerror = (error) => {
            //     console.error('WebSocket错误:', error);
            //     // 如果WebSocket连接失败，回退到随机数据模式
            //     this.startRandomDataFallback();
            // };
            
            this.socket.onclose = () => {
                console.log('WebSocket连接已关闭');
                // 尝试重新连接
                setTimeout(() => {
                    this.connectSocket();
                }, 3000);
            };
            
        } catch (error) {
            console.error('WebSocket连接失败:', error);
            this.startRandomDataFallback();
        }
    }

    startRandomDataFallback() {
        // 如果socket连接失败，使用随机数据作为备选方案
        console.log('使用随机数据模式作为备选方案');
        setInterval(() => this.updateRandomData(), 5000);
    }

    updateBasicDataFromSocket(data) {
        // 从socket接收的数据更新基本数据和高级数据
        if (data && data.basic) {
            // 更新基础数据
            if (data.basic.light && data.basic.music && data.basic.curtain && data.basic.Scores) {
                this.updateBasicData(data.basic);
                // 同时更新图表
                this.updateChart(data.basic.Scores);
            }
            
            // 更新算法分析数据
            if (data.basic.algorithm_analysis) {
                this.updateAlgorithmAnalysis(data.basic.algorithm_analysis);
            }
        }
        
        if (data && data.advanced) {
            // 更新高级数据
            if (data.advanced.State && data.advanced.Summary && data.advanced.Action) {
                this.updateAdvancedData(data.advanced);
                // 更新状态历史图表
                this.updateStateHistory(data.advanced.State);
            }
            
            // 更新高级算法分析数据
            if (data.advanced.clinical_analysis || data.advanced.cognitive_analysis) {
                this.updateAdvancedAlgorithmAnalysis(data.advanced.clinical_analysis, data.advanced.cognitive_analysis);
            }
        }
    }

    updateDateTime() {
        const now = new Date();
        const options = {
            year: 'numeric',
            month: 'long',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
            weekday: 'long'
        };
        
        document.getElementById('datetime').textContent = 
            now.toLocaleDateString('zh-CN', options);
    }

    loadSampleData() {
        // Load basic data
        this.updateBasicData({
            "light": { 
                "is_on": true, 
                "color_hex": "#FF5733", 
                "lightness": 75 
            },
            "music": { 
                "is_playing": true, 
                "name": "Aria De Capo", 
                "type": "Relaxing" 
            },
            "curtain": { 
                "state": 0 
            },
            "Scores": {
                "At": 68, 
                "Ex": 45, 
                "Re": 72, 
                "St": 35
            },
        });

        // Load advanced data
        this.updateAdvancedData({
            "State": "Relaxed",
            "Summary": "用户当前处于放松状态，建议播放轻柔音乐并调暗灯光以维持这种状态。脑电信号显示专注度适中，压力水平较低，这是一个良好的工作或休息状态。",
            "Action": "Adjusting Light & Music"
        });
    }

    updateBasicData(data) {
        // Update light data
        const lightStatus = document.getElementById('light-status');
        const lightPreview = document.getElementById('light-preview');
        const lightColor = document.getElementById('light-color');
        const lightBrightness = document.getElementById('light-brightness');

        if (data.light.is_on) {
            lightStatus.className = 'status-indicator on';
            lightPreview.style.background = data.light.color_hex;
            lightPreview.style.boxShadow = `0 0 30px ${data.light.color_hex}80`;
        } else {
            lightStatus.className = 'status-indicator off';
            lightPreview.style.background = '#4a5568';
            lightPreview.style.boxShadow = 'none';
        }

        lightColor.textContent = data.light.color_hex;
        lightBrightness.textContent = `${data.light.lightness}%`;

        // Update music data
        const musicStatus = document.getElementById('music-status');
        const songName = document.getElementById('song-name');
        const songType = document.getElementById('song-type');

        if (data.music.is_playing) {
            musicStatus.className = 'status-indicator on';
        } else {
            musicStatus.className = 'status-indicator off';
        }

        songName.textContent = data.music.name;
        songType.textContent = data.music.type;

        // Update curtain data
        const curtainIcon = document.getElementById('curtain-icon');
        const curtainState = document.getElementById('curtain-state');

        if (data.curtain.state === 0) {
            curtainIcon.className = 'fas fa-window-maximize';
            curtainState.textContent = '开启';
            curtainState.style.color = 'var(--success-color)';
        } else {
            curtainIcon.className = 'fas fa-window-minimize';
            curtainState.textContent = '关闭';
            curtainState.style.color = 'var(--error-color)';
        }

        // Update scores
        this.updateScores(data.Scores);
    }

    updateScores(scores) {
        const scoreMapping = {
            'At': 'attention',
            'Ex': 'excitement', 
            'Re': 'relaxation',
            'St': 'stress'
        };

        Object.entries(scores).forEach(([key, value]) => {
            const scoreName = scoreMapping[key];
            if (scoreName) {
                const scoreElement = document.getElementById(`${scoreName}-score`);
                const fillElement = document.getElementById(`${scoreName}-fill`);
                
                if (scoreElement && fillElement) {
                    scoreElement.textContent = value;
                    fillElement.style.width = `${value}%`;
                    
                    // Add color based on score range
                    if (value >= 70) {
                        fillElement.style.background = 'linear-gradient(90deg, var(--success-color), #059669)';
                    } else if (value >= 40) {
                        fillElement.style.background = 'linear-gradient(90deg, var(--warning-color), #f97316)';
                    } else {
                        fillElement.style.background = 'linear-gradient(90deg, var(--error-color), #dc2626)';
                    }
                }
            }
        });
    }

    updateAdvancedData(data) {
        // Update current state
        const stateIcon = document.getElementById('state-icon');
        const currentState = document.getElementById('current-state');
        
        currentState.textContent = data.State;
        
        // Set state icon based on state
        const stateConfig = {
            'Stress': { icon: 'fas fa-exclamation-triangle', color: 'var(--error-color)' },
            'Relaxed': { icon: 'fas fa-leaf', color: 'var(--success-color)' },
            'Focused': { icon: 'fas fa-eye', color: 'var(--primary-color)' },
            'Excited': { icon: 'fas fa-bolt', color: 'var(--warning-color)' }
        };
        
        const config = stateConfig[data.State] || stateConfig['Stress'];
        stateIcon.innerHTML = `<i class="${config.icon}"></i>`;
        stateIcon.style.color = config.color;

        // Update AI summary
        const aiSummary = document.getElementById('ai-summary');
        aiSummary.textContent = data.Summary;

        // Update system action
        const actionIcon = document.getElementById('action-icon');
        const systemAction = document.getElementById('system-action');
        
        systemAction.textContent = data.Action;
        
        // Set action icon based on action type
        const actionConfig = {
            'Notify': { icon: 'fas fa-bell' },
            'Adjusting Light & Music': { icon: 'fas fa-sliders-h' },
            'Meditation': { icon: 'fas fa-om' },
            'Break Reminder': { icon: 'fas fa-pause-circle' }
        };
        
        const actionIconConfig = actionConfig[data.Action] || actionConfig['Notify'];
        actionIcon.className = actionIconConfig.icon;
    }

    updateRandomData() {
        // Generate random data for demonstration
        const randomScores = {
            At: Math.floor(Math.random() * 40) + 30, // 30-70
            Ex: Math.floor(Math.random() * 60) + 20, // 20-80
            Re: Math.floor(Math.random() * 50) + 30, // 30-80
            St: Math.floor(Math.random() * 40) + 10  // 10-50
        };

        const states = ['Relaxed', 'Focused', 'Stressed', 'Excited'];
        const actions = ['Notify', 'Adjusting Light & Music', 'Meditation', 'Break Reminder'];
        
        const randomState = states[Math.floor(Math.random() * states.length)];
        const randomAction = actions[Math.floor(Math.random() * actions.length)];

        // Update basic data with random values
        this.updateBasicData({
            "light": { 
                "is_on": Math.random() > 0.2, 
                "color_hex": this.getRandomColor(), 
                "lightness": Math.floor(Math.random() * 80) + 20 
            },
            "music": { 
                "is_playing": Math.random() > 0.3,
                "name": "Aria De Capo", 
                "type": "Relaxing" 
            },
            "curtain": { 
                "state": Math.random() > 0.5 ? 0 : 1 
            },
            "Scores": randomScores
        });

        // Update advanced data
        this.updateAdvancedData({
            "State": randomState,
            "Summary": this.generateSummary(randomState, randomScores),
            "Action": randomAction
        });

        // Update chart
        this.updateChart(randomScores);
    }

    getRandomColor() {
        const colors = ['#FF5733', '#33FF57', '#3357FF', '#FF33F5', '#F5FF33', '#33F5FF'];
        return colors[Math.floor(Math.random() * colors.length)];
    }

    generateSummary(state, scores) {
        const summaries = {
            'Relaxed': `用户当前处于放松状态，专注度为${scores.At}，压力水平较低(${scores.St})。建议维持当前环境设置，继续播放轻柔音乐。`,
            'Focused': `用户专注度较高(${scores.At})，建议保持当前环境以维持专注状态。兴奋度为${scores.Ex}，适合进行复杂的工作任务。`,
            'Stressed': `检测到用户压力水平升高(${scores.St})，建议播放放松音乐并调暗灯光。专注度为${scores.At}，建议适当休息。`,
            'Excited': `用户兴奋度较高(${scores.Ex})，精神状态活跃。可以进行创造性工作，但注意避免过度刺激。`
        };
        
        return summaries[state] || summaries['Relaxed'];
    }

    initChart() {
        const ctx = document.getElementById('trendsChart').getContext('2d');
        
        this.trendsChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [
                    {
                        label: '专注值',
                        data: [],
                        borderColor: '#6366f1',
                        backgroundColor: 'rgba(99, 102, 241, 0.1)',
                        tension: 0.4,
                        fill: true
                    },
                    {
                        label: '兴奋值',
                        data: [],
                        borderColor: '#f59e0b',
                        backgroundColor: 'rgba(245, 158, 11, 0.1)',
                        tension: 0.4,
                        fill: true
                    },
                    {
                        label: '放松度',
                        data: [],
                        borderColor: '#10b981',
                        backgroundColor: 'rgba(16, 185, 129, 0.1)',
                        tension: 0.4,
                        fill: true
                    },
                    {
                        label: '紧张度',
                        data: [],
                        borderColor: '#ef4444',
                        backgroundColor: 'rgba(239, 68, 68, 0.1)',
                        tension: 0.4,
                        fill: true
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        labels: {
                            color: '#cbd5e1'
                        }
                    }
                },
                scales: {
                    x: {
                        ticks: {
                            color: '#94a3b8'
                        },
                        grid: {
                            color: '#475569'
                        }
                    },
                    y: {
                        beginAtZero: true,
                        max: 100,
                        ticks: {
                            color: '#94a3b8'
                        },
                        grid: {
                            color: '#475569'
                        }
                    }
                }
            }
        });

        // Initialize with some sample data
        this.initChartData();
    }

    initStateHistoryChart() {
        const ctx = document.getElementById('stateHistoryChart').getContext('2d');
        
        this.stateHistoryChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: '精神状态',
                    data: [],
                    borderColor: '#8b5cf6',
                    backgroundColor: 'rgba(139, 92, 246, 0.1)',
                    tension: 0.4,
                    fill: true,
                    pointRadius: 4,
                    pointBackgroundColor: '#8b5cf6'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        labels: {
                            color: '#cbd5e1'
                        }
                    }
                },
                scales: {
                    x: {
                        ticks: {
                            color: '#94a3b8'
                        },
                        grid: {
                            color: '#475569'
                        }
                    },
                    y: {
                        type: 'category',
                        labels: ['RELAXED', 'NEUTRAL', 'FOCUSED', 'STRESSED', 'DISTRACTED', 'FATIGUED'],
                        ticks: {
                            color: '#94a3b8'
                        },
                        grid: {
                            color: '#475569'
                        }
                    }
                }
            }
        });
    }

    initChartData() {
        const now = new Date();
        for (let i = 9; i >= 0; i--) {
            const time = new Date(now.getTime() - i * 30000); // 30 seconds intervals
            const timeStr = time.toLocaleTimeString('zh-CN', { 
                hour: '2-digit', 
                minute: '2-digit', 
                second: '2-digit' 
            });
            
            this.trendsChart.data.labels.push(timeStr);
            this.trendsChart.data.datasets[0].data.push(Math.floor(Math.random() * 40) + 30);
            this.trendsChart.data.datasets[1].data.push(Math.floor(Math.random() * 60) + 20);
            this.trendsChart.data.datasets[2].data.push(Math.floor(Math.random() * 50) + 30);
            this.trendsChart.data.datasets[3].data.push(Math.floor(Math.random() * 40) + 10);
        }
        
        this.trendsChart.update();
    }

    updateChart(scores) {
        const now = new Date();
        const timeStr = now.toLocaleTimeString('zh-CN', { 
            hour: '2-digit', 
            minute: '2-digit', 
            second: '2-digit' 
        });

        // Remove old data if we have more than 20 points
        if (this.trendsChart.data.labels.length >= 20) {
            this.trendsChart.data.labels.shift();
            this.trendsChart.data.datasets.forEach(dataset => {
                dataset.data.shift();
            });
        }

        // Add new data
        this.trendsChart.data.labels.push(timeStr);
        this.trendsChart.data.datasets[0].data.push(scores.At);
        this.trendsChart.data.datasets[1].data.push(scores.Ex);
        this.trendsChart.data.datasets[2].data.push(scores.Re);
        this.trendsChart.data.datasets[3].data.push(scores.St);

        this.trendsChart.update('none'); // Smooth update without animation
    }

    updateStateHistory(currentState) {
        const now = new Date();
        const timeStr = now.toLocaleTimeString('zh-CN', { 
            hour: '2-digit', 
            minute: '2-digit', 
            second: '2-digit' 
        });

        // Remove old data if we have more than 20 points
        if (this.stateHistoryChart.data.labels.length >= 20) {
            this.stateHistoryChart.data.labels.shift();
            this.stateHistoryChart.data.datasets[0].data.shift();
        }

        // Add new data
        this.stateHistoryChart.data.labels.push(timeStr);
        this.stateHistoryChart.data.datasets[0].data.push(currentState);

        this.stateHistoryChart.update('none'); // Smooth update without animation
    }

    initAlgorithmTrendsChart() {
        const ctx = document.getElementById('algorithmTrendsChart').getContext('2d');
        
        this.algorithmTrendsChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [
                    {
                        label: 'FAA Z-Score',
                        data: [],
                        borderColor: '#ef4444',
                        backgroundColor: 'rgba(239, 68, 68, 0.1)',
                        tension: 0.4,
                        fill: false,
                        yAxisID: 'y'
                    },
                    {
                        label: 'Theta Z-Score',
                        data: [],
                        borderColor: '#f59e0b',
                        backgroundColor: 'rgba(245, 158, 11, 0.1)',
                        tension: 0.4,
                        fill: false,
                        yAxisID: 'y'
                    },
                    {
                        label: '参与度指数',
                        data: [],
                        borderColor: '#10b981',
                        backgroundColor: 'rgba(16, 185, 129, 0.1)',
                        tension: 0.4,
                        fill: false,
                        yAxisID: 'y1'
                    },
                    {
                        label: '疲劳指数',
                        data: [],
                        borderColor: '#8b5cf6',
                        backgroundColor: 'rgba(139, 92, 246, 0.1)',
                        tension: 0.4,
                        fill: false,
                        yAxisID: 'y1'
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        labels: {
                            color: '#cbd5e1'
                        }
                    }
                },
                scales: {
                    x: {
                        ticks: {
                            color: '#94a3b8'
                        },
                        grid: {
                            color: '#475569'
                        }
                    },
                    y: {
                        type: 'linear',
                        display: true,
                        position: 'left',
                        title: {
                            display: true,
                            text: 'Z-Score',
                            color: '#cbd5e1'
                        },
                        ticks: {
                            color: '#94a3b8'
                        },
                        grid: {
                            color: '#475569'
                        }
                    },
                    y1: {
                        type: 'linear',
                        display: true,
                        position: 'right',
                        title: {
                            display: true,
                            text: '指数',
                            color: '#cbd5e1'
                        },
                        ticks: {
                            color: '#94a3b8'
                        },
                        grid: {
                            drawOnChartArea: false,
                            color: '#475569'
                        }
                    }
                }
            }
        });
    }

    updateAlgorithmAnalysis(algorithmData) {
        if (!algorithmData) return;

        // 更新临床分析
        if (algorithmData.clinical_analysis) {
            const clinical = algorithmData.clinical_analysis;
            
            // 更新临床状态
            const clinicalState = document.getElementById('clinical-state');
            if (clinicalState) {
                clinicalState.textContent = clinical.state || 'UNKNOWN';
                // 根据状态设置颜色
                if (clinical.state && clinical.state.includes('HIGH_DEPRESSIVE_RISK')) {
                    clinicalState.style.color = 'var(--error-color)';
                } else if (clinical.state && clinical.state.includes('MODERATE_DEPRESSIVE_RISK')) {
                    clinicalState.style.color = 'var(--warning-color)';
                } else {
                    clinicalState.style.color = 'var(--success-color)';
                }
            }

            // 更新FAA Z-Score
            const faaScore = document.getElementById('faa-z-score');
            const faaFill = document.getElementById('faa-fill');
            if (faaScore && clinical.faa_z_score !== undefined) {
                faaScore.textContent = clinical.faa_z_score.toFixed(2);
                // 将Z-score转换为百分比显示(限制在0-100%)
                const faaPercent = Math.max(0, Math.min(100, (clinical.faa_z_score + 3) * 16.67)); // -3到+3映射到0-100%
                faaFill.style.width = `${faaPercent}%`;
                
                if (clinical.faa_z_score > 2.5) {
                    faaFill.style.background = 'linear-gradient(90deg, var(--error-color), #dc2626)';
                } else if (clinical.faa_z_score > 2.0) {
                    faaFill.style.background = 'linear-gradient(90deg, var(--warning-color), #f97316)';
                } else {
                    faaFill.style.background = 'linear-gradient(90deg, var(--success-color), #059669)';
                }
            }

            // 更新Theta Z-Score
            const thetaScore = document.getElementById('theta-z-score');
            const thetaFill = document.getElementById('theta-fill');
            if (thetaScore && clinical.theta_z_score !== undefined) {
                thetaScore.textContent = clinical.theta_z_score.toFixed(2);
                const thetaPercent = Math.max(0, Math.min(100, (clinical.theta_z_score + 3) * 16.67));
                thetaFill.style.width = `${thetaPercent}%`;
                
                if (clinical.theta_z_score > 2.5) {
                    thetaFill.style.background = 'linear-gradient(90deg, var(--error-color), #dc2626)';
                } else if (clinical.theta_z_score > 2.0) {
                    thetaFill.style.background = 'linear-gradient(90deg, var(--warning-color), #f97316)';
                } else {
                    thetaFill.style.background = 'linear-gradient(90deg, var(--success-color), #059669)';
                }
            }

            // 更新临床详情
            const clinicalDetails = document.getElementById('clinical-details');
            if (clinicalDetails && clinical.details) {
                clinicalDetails.textContent = clinical.details;
            }
        }

        // 更新认知分析
        if (algorithmData.cognitive_analysis) {
            const cognitive = algorithmData.cognitive_analysis;
            
            // 更新认知状态
            const cognitiveState = document.getElementById('cognitive-state');
            if (cognitiveState) {
                cognitiveState.textContent = cognitive.state || 'UNKNOWN';
                // 根据状态设置颜色
                if (cognitive.state === 'FATIGUE_DROWSINESS') {
                    cognitiveState.style.color = 'var(--error-color)';
                } else if (cognitive.state === 'HIGH_ENGAGEMENT_EXCITEMENT') {
                    cognitiveState.style.color = 'var(--success-color)';
                } else if (cognitive.state === 'RELAXED_IDLE') {
                    cognitiveState.style.color = 'var(--primary-color)';
                } else {
                    cognitiveState.style.color = 'var(--text-color)';
                }
            }

            // 更新参与度指数
            const engagementIndex = document.getElementById('engagement-index');
            const engagementFill = document.getElementById('engagement-fill');
            if (engagementIndex && cognitive.engagement_index !== undefined) {
                engagementIndex.textContent = cognitive.engagement_index.toFixed(2);
                // 将指数转换为百分比 (假设0-3的范围)
                const engagementPercent = Math.max(0, Math.min(100, cognitive.engagement_index * 33.33));
                engagementFill.style.width = `${engagementPercent}%`;
                
                if (cognitive.engagement_index > 1.8) {
                    engagementFill.style.background = 'linear-gradient(90deg, var(--success-color), #059669)';
                } else if (cognitive.engagement_index < 0.6) {
                    engagementFill.style.background = 'linear-gradient(90deg, var(--primary-color), #0ea5e9)';
                } else {
                    engagementFill.style.background = 'linear-gradient(90deg, var(--warning-color), #f97316)';
                }
            }

            // 更新疲劳指数
            const fatigueIndex = document.getElementById('fatigue-index');
            const fatigueFill = document.getElementById('fatigue-fill');
            if (fatigueIndex && cognitive.fatigue_index !== undefined) {
                fatigueIndex.textContent = cognitive.fatigue_index.toFixed(2);
                // 将指数转换为百分比 (假设0-2的范围)
                const fatiguePercent = Math.max(0, Math.min(100, cognitive.fatigue_index * 50));
                fatigueFill.style.width = `${fatiguePercent}%`;
                
                if (cognitive.fatigue_index > 1.2) {
                    fatigueFill.style.background = 'linear-gradient(90deg, var(--error-color), #dc2626)';
                } else {
                    fatigueFill.style.background = 'linear-gradient(90deg, var(--success-color), #059669)';
                }
            }

            // 更新认知详情
            const cognitiveDetails = document.getElementById('cognitive-details');
            if (cognitiveDetails && cognitive.details) {
                cognitiveDetails.textContent = cognitive.details;
            }
        }

        // 更新算法趋势图表
        this.updateAlgorithmTrendsChart(algorithmData);
    }

    updateAdvancedAlgorithmAnalysis(clinicalAnalysis, cognitiveAnalysis) {
        // 此函数处理来自advanced数据的算法分析
        // 目前clinical_analysis和cognitive_analysis已经通过basic.algorithm_analysis处理
        // 这里可以添加额外的高级分析处理逻辑
        console.log('Advanced algorithm analysis updated:', { clinicalAnalysis, cognitiveAnalysis });
    }

    updateAlgorithmTrendsChart(algorithmData) {
        if (!this.algorithmTrendsChart || !algorithmData) return;

        const now = new Date();
        const timeStr = now.toLocaleTimeString('zh-CN', { 
            hour: '2-digit', 
            minute: '2-digit', 
            second: '2-digit' 
        });

        // 移除旧数据（保持最近20个数据点）
        if (this.algorithmTrendsChart.data.labels.length >= 20) {
            this.algorithmTrendsChart.data.labels.shift();
            this.algorithmTrendsChart.data.datasets.forEach(dataset => {
                dataset.data.shift();
            });
        }

        // 添加新数据
        this.algorithmTrendsChart.data.labels.push(timeStr);
        
        // FAA Z-Score
        const faaZScore = algorithmData.clinical_analysis?.faa_z_score || 0;
        this.algorithmTrendsChart.data.datasets[0].data.push(faaZScore);
        
        // Theta Z-Score  
        const thetaZScore = algorithmData.clinical_analysis?.theta_z_score || 0;
        this.algorithmTrendsChart.data.datasets[1].data.push(thetaZScore);
        
        // 参与度指数
        const engagementIndex = algorithmData.cognitive_analysis?.engagement_index || 0;
        this.algorithmTrendsChart.data.datasets[2].data.push(engagementIndex);
        
        // 疲劳指数
        const fatigueIndex = algorithmData.cognitive_analysis?.fatigue_index || 0;
        this.algorithmTrendsChart.data.datasets[3].data.push(fatigueIndex);

        this.algorithmTrendsChart.update('none'); // 平滑更新无动画
    }
}

// Global functions for tab switching
function showTab(tabName) {
    // Hide all pages
    document.querySelectorAll('.page').forEach(page => {
        page.classList.remove('active');
    });
    
    // Remove active class from all tabs
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    
    // Show selected page
    document.getElementById(`${tabName}-page`).classList.add('active');
    
    // Add active class to selected tab
    document.getElementById(`${tabName}-tab`).classList.add('active');
}

// API functions for external data updates
window.updateDashboardData = function(basicData, advancedData) {
    if (window.dashboard) {
        if (basicData) {
            window.dashboard.updateBasicData(basicData);
        }
        if (advancedData) {
            window.dashboard.updateAdvancedData(advancedData);
        }
    }
};

// Initialize dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    window.dashboard = new MindDaemonDashboard();
    console.log('Mind Daemon Dashboard initialized successfully!');
});

// Example usage:
// To update data from external scripts, use:
// updateDashboardData(basic_params, advanced_params);