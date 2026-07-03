/**
 * Machine Learning Trainer Dashboard Controller
 * Manages model execution triggers and renders training curves
 */

document.addEventListener('DOMContentLoaded', function() {
    const trainSymbolSelect = document.getElementById('trainSymbolSelect');
    
    // Classical ML Elements
    const trainClassicalBtn = document.getElementById('trainClassicalBtn');
    const classicalStepsCard = document.getElementById('classicalStepsCard');
    
    // LSTM Elements
    const trainLstmBtn = document.getElementById('trainLstmBtn');
    const lstmStepsCard = document.getElementById('lstmStepsCard');
    const lstmEpochs = document.getElementById('lstmEpochs');
    const lstmLookback = document.getElementById('lstmLookback');
    const lstmBatchSize = document.getElementById('lstmBatchSize');
    const lstmChartCard = document.getElementById('lstmChartCard');
    
    // Feature Importance Elements
    const featureImportanceCard = document.getElementById('featureImportanceCard');
    const importanceModelSelect = document.getElementById('importanceModelSelect');

    // Table Body
    const performanceTableBody = document.getElementById('performanceTableBody');

    // Helper to simulate smooth step progress
    function simulateProgress(prefix, stepsCount, durationPerStep, callback) {
        let current = 1;
        
        function activateStep(stepIdx) {
            // Mark previous steps as completed
            for (let i = 1; i < stepIdx; i++) {
                const item = document.getElementById(`${prefix}-step-${i}`);
                const icon = document.getElementById(`${prefix}-icon-${i}`);
                const text = document.getElementById(`${prefix}-text-${i}`);
                if (item) {
                    item.className = 'training-step-item completed animate-fade-in';
                    icon.className = 'bi bi-check-circle-fill text-success fs-5';
                    text.className = 'small text-success fw-semibold';
                }
            }
            
            // Mark current step as active
            const item = document.getElementById(`${prefix}-step-${stepIdx}`);
            const icon = document.getElementById(`${prefix}-icon-${stepIdx}`);
            const text = document.getElementById(`${prefix}-text-${stepIdx}`);
            if (item) {
                item.className = 'training-step-item active';
                icon.className = 'bi bi-arrow-right-circle-fill text-primary fs-5';
                text.className = 'small text-white fw-bold';
            }
        }
        
        // Reset all steps to pending
        for (let i = 1; i <= stepsCount; i++) {
            const item = document.getElementById(`${prefix}-step-${i}`);
            const icon = document.getElementById(`${prefix}-icon-${i}`);
            const text = document.getElementById(`${prefix}-text-${i}`);
            if (item) {
                item.className = 'training-step-item pending';
                icon.className = 'bi bi-circle text-secondary fs-5';
                text.className = 'small text-secondary';
            }
        }
        
        activateStep(1);
        
        const interval = setInterval(() => {
            current++;
            if (current <= stepsCount) {
                activateStep(current);
            } else {
                clearInterval(interval);
                if (callback) callback();
            }
        }, durationPerStep);
        
        return interval;
    }

    // Chart styling variable
    const darkTemplate = {
        layout: {
            plot_bgcolor: 'rgba(0,0,0,0)',
            paper_bgcolor: 'rgba(0,0,0,0)',
            font: { color: '#f8fafc', family: 'Inter, sans-serif' },
            xaxis: {
                gridcolor: 'rgba(255, 255, 255, 0.05)',
                linecolor: 'rgba(255, 255, 255, 0.1)',
                zerolinecolor: 'rgba(255, 255, 255, 0.1)'
            },
            yaxis: {
                gridcolor: 'rgba(255, 255, 255, 0.05)',
                linecolor: 'rgba(255, 255, 255, 0.1)',
                zerolinecolor: 'rgba(255, 255, 255, 0.1)'
            }
        }
    };

    // Load leaderboard for selected symbol on startup (synchronized with dashboard & chatbot context)
    const storedSymbol = localStorage.getItem('activeStockSymbol');
    if (storedSymbol && Array.from(trainSymbolSelect.options).some(opt => opt.value === storedSymbol)) {
        trainSymbolSelect.value = storedSymbol;
    }
    loadLeaderboard(trainSymbolSelect.value);
    loadFeatureImportance(trainSymbolSelect.value, importanceModelSelect.value);
    updateSymbolSummary(trainSymbolSelect.value);

    // Bind stock selection change
    trainSymbolSelect.addEventListener('change', function(e) {
        localStorage.setItem('activeStockSymbol', e.target.value);
        lstmChartCard.classList.add('d-none');
        loadLeaderboard(e.target.value);
        loadFeatureImportance(e.target.value, importanceModelSelect.value);
        updateSymbolSummary(e.target.value);
    });

    importanceModelSelect.addEventListener('change', function(e) {
        loadFeatureImportance(trainSymbolSelect.value, e.target.value);
    });

    // Train Classical Models
    trainClassicalBtn.addEventListener('click', function() {
        const symbol = trainSymbolSelect.value;
        
        trainClassicalBtn.disabled = true;
        trainLstmBtn.disabled = true;
        classicalStepsCard.classList.remove('d-none');
        
        const progressInterval = simulateProgress('class', 6, 1200);
        
        fetch(`/api/train/ml/${symbol}`, {
            method: 'POST'
        })
        .then(response => response.json())
        .then(data => {
            clearInterval(progressInterval);
            // Instantly complete all checklist items
            for (let i = 1; i <= 6; i++) {
                const item = document.getElementById(`class-step-${i}`);
                const icon = document.getElementById(`class-icon-${i}`);
                const text = document.getElementById(`class-text-${i}`);
                if (item) {
                    item.className = 'training-step-item completed';
                    icon.className = 'bi bi-check-circle-fill text-success fs-5';
                    text.className = 'small text-success fw-semibold';
                }
            }
            
            setTimeout(() => {
                trainClassicalBtn.disabled = false;
                trainLstmBtn.disabled = false;
                classicalStepsCard.classList.add('d-none');
                
                if (data.success) {
                    loadLeaderboard(symbol);
                    loadFeatureImportance(symbol, importanceModelSelect.value);
                } else {
                    alert("Training failed: " + data.error);
                }
            }, 800);
        })
        .catch(err => {
            clearInterval(progressInterval);
            trainClassicalBtn.disabled = false;
            trainLstmBtn.disabled = false;
            classicalStepsCard.classList.add('d-none');
            console.error(err);
        });
    });

    // Train LSTM Model
    trainLstmBtn.addEventListener('click', function() {
        const symbol = trainSymbolSelect.value;
        const epochs = lstmEpochs.value;
        const lookback = lstmLookback.value;
        
        trainClassicalBtn.disabled = true;
        trainLstmBtn.disabled = true;
        lstmStepsCard.classList.remove('d-none');
        lstmChartCard.classList.add('d-none');
        
        const progressInterval = simulateProgress('lstm', 6, 2200);
        
        const batchSize = lstmBatchSize ? lstmBatchSize.value : 32;
        
        fetch(`/api/train/lstm/${symbol}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                epochs: epochs,
                lookback: lookback,
                batch_size: batchSize
            })
        })
        .then(response => response.json())
        .then(data => {
            clearInterval(progressInterval);
            // Instantly complete all checklist items
            for (let i = 1; i <= 6; i++) {
                const item = document.getElementById(`lstm-step-${i}`);
                const icon = document.getElementById(`lstm-icon-${i}`);
                const text = document.getElementById(`lstm-text-${i}`);
                if (item) {
                    item.className = 'training-step-item completed';
                    icon.className = 'bi bi-check-circle-fill text-success fs-5';
                    text.className = 'small text-success fw-semibold';
                }
            }
            
            setTimeout(() => {
                trainClassicalBtn.disabled = false;
                trainLstmBtn.disabled = false;
                lstmStepsCard.classList.add('d-none');
                
                if (data.success) {
                    loadLeaderboard(symbol);
                    renderLossChart(data.loss_history, data.val_loss_history);
                } else {
                    alert("LSTM Training failed: " + data.error);
                }
            }, 800);
        })
        .catch(err => {
            clearInterval(progressInterval);
            trainClassicalBtn.disabled = false;
            trainLstmBtn.disabled = false;
            lstmStepsCard.classList.add('d-none');
            console.error(err);
        });
    });

    function loadLeaderboard(symbol) {
        fetch(`/api/performance/${symbol}`)
        .then(response => response.json())
        .then(data => {
            if (data.success && data.performance.length > 0) {
                performanceTableBody.innerHTML = '';
                data.performance.forEach((p, index) => {
                    const isWinner = index === 0;
                    
                    // Gamified leaderboard rank icons
                    let rankIcon = '';
                    if (index === 0) rankIcon = '<span class="me-2" style="font-size: 1.1rem;" title="1st Place (Winner)">🥇</span>';
                    else if (index === 1) rankIcon = '<span class="me-2" style="font-size: 1.1rem;" title="2nd Place">🥈</span>';
                    else if (index === 2) rankIcon = '<span class="me-2" style="font-size: 1.1rem;" title="3rd Place">🥉</span>';
                    else rankIcon = `<span class="me-2 small text-muted font-monospace" style="width: 20px; display: inline-block;">#${index + 1}</span>`;
                    
                    const row = `
                        <tr class="${isWinner ? 'leaderboard-winner animate-fade-in' : ''}">
                            <td class="fw-semibold text-white d-flex align-items-center">
                                ${rankIcon}
                                <span>${p.model_name}</span>
                                ${isWinner ? '<span class="badge bg-warning-subtle text-warning border border-warning-subtle ms-2 py-0.5 px-2 animate-pulse" style="font-size: 0.65rem; border-radius: 4px; animation: pulseGlow 2s infinite;"><i class="bi bi-trophy-fill me-1"></i>Best Model</span>' : ''}
                            </td>
                            <td>${p.mae.toFixed(4)}</td>
                            <td>${p.rmse.toFixed(4)}</td>
                            <td class="${p.r2 >= 0 ? 'text-success fw-semibold' : 'text-danger'}">${p.r2.toFixed(4)}</td>
                            <td>${p.mape.toFixed(2)}%</td>
                        </tr>
                    `;
                    performanceTableBody.innerHTML += row;
                });
            } else {
                performanceTableBody.innerHTML = `
                    <tr>
                        <td colspan="5" class="text-center text-secondary small">No cached models found for ${symbol}. Trigger training.</td>
                    </tr>
                `;
            }
        })
        .catch(err => console.error("Error loading performance table:", err));
    }

    function renderLossChart(losses, valLosses) {
        lstmChartCard.classList.remove('d-none');
        
        const epochsX = Array.from({length: losses.length}, (_, i) => i + 1);
        
        const traceLoss = {
            x: epochsX,
            y: losses,
            mode: 'lines+markers',
            name: 'Training Loss',
            line: { color: '#3b82f6', width: 2 }
        };
        
        const traceValLoss = {
            x: epochsX,
            y: valLosses,
            mode: 'lines+markers',
            name: 'Validation Loss',
            line: { color: '#10b981', width: 2 }
        };
        
        const layout = {
            margin: { t: 30, r: 20, b: 40, l: 50 },
            xaxis: {
                title: 'Epoch',
                dtick: 1,
                ...darkTemplate.layout.xaxis
            },
            yaxis: {
                title: 'MSE Loss',
                ...darkTemplate.layout.yaxis
            },
            legend: { orientation: 'h', y: 1.1, x: 0 },
            ...darkTemplate.layout
        };
        
        Plotly.newPlot('plotlyLstmLossChart', [traceLoss, traceValLoss], layout, { responsive: true, displayModeBar: false });
    }

    function loadFeatureImportance(symbol, model) {
        fetch(`/api/feature_importance/${symbol}?model=${model}`)
        .then(response => response.json())
        .then(data => {
            if (data.success && data.features.length > 0) {
                featureImportanceCard.classList.remove('d-none');
                
                // Sort reverse for Plotly horizontal bar chart
                const sorted = [...data.features].reverse();
                const names = sorted.map(f => f.name);
                const values = sorted.map(f => f.importance);
                
                // Generate a visual gradient of opacity from green
                const colors = values.map((val, idx) => {
                    const ratio = idx / (values.length - 1);
                    return `rgba(16, 185, 129, ${0.4 + ratio * 0.6})`;
                });
                
                const trace = {
                    x: values,
                    y: names,
                    type: 'bar',
                    orientation: 'h',
                    marker: {
                        color: colors,
                        line: { color: 'rgba(16, 185, 129, 1)', width: 1 }
                    }
                };
                
                const layout = {
                    margin: { t: 10, r: 20, b: 30, l: 150 },
                    xaxis: {
                        title: 'Relative Importance Score',
                        ...darkTemplate.layout.xaxis
                    },
                    yaxis: {
                        ...darkTemplate.layout.yaxis
                    },
                    ...darkTemplate.layout
                };
                
                Plotly.newPlot('plotlyFeatureImportanceChart', [trace], layout, { responsive: true, displayModeBar: false });
            } else {
                featureImportanceCard.classList.add('d-none');
            }
        })
        .catch(err => {
            console.error("Error loading feature importance:", err);
            featureImportanceCard.classList.add('d-none');
        });
    }

    function updateSymbolSummary(symbol) {
        const hud = document.getElementById('trainSymbolHud');
        const span = document.getElementById('trainSpan');
        const rows = document.getElementById('trainRows');
        const close = document.getElementById('trainClose');
        
        if (!hud) return;
        
        fetch(`/api/stock/${symbol}`)
        .then(res => res.json())
        .then(data => {
            if (data && data.close && data.close.length > 0) {
                hud.classList.remove('d-none');
                rows.innerText = `${data.close.length} rows`;
                
                const start = data.dates[0];
                const end = data.dates[data.dates.length - 1];
                span.innerText = `${start} to ${end}`;
                
                const lastClose = data.close[data.close.length - 1];
                const change = data.close[data.close.length - 1] - data.close[data.close.length - 2];
                const pct = (change / data.close[data.close.length - 2]) * 100;
                
                close.innerText = `$${lastClose.toFixed(2)} (${change >= 0 ? '+' : ''}${pct.toFixed(2)}%)`;
                close.className = change >= 0 ? 'small fw-bold text-success' : 'small fw-bold text-danger';
            } else {
                hud.classList.add('d-none');
            }
        })
        .catch(err => {
            console.error("Error loading training symbol HUD:", err);
            hud.classList.add('d-none');
        });
    }
});
