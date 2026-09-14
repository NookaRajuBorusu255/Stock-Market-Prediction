/**
 * Advanced ML Trainer Dashboard Controller v2.0
 * Manages model training, live prediction, backtest charts, 30-day LSTM forecast
 */

document.addEventListener('DOMContentLoaded', function () {

    // ── Element References ──────────────────────────────────────
    const trainSymbolSelect     = document.getElementById('trainSymbolSelect');
    const trainClassicalBtn     = document.getElementById('trainClassicalBtn');
    const trainLstmBtn          = document.getElementById('trainLstmBtn');
    const lstmEpochs            = document.getElementById('lstmEpochs');
    const lstmLookback          = document.getElementById('lstmLookback');
    const lstmBatchSize         = document.getElementById('lstmBatchSize');
    const lstmChartCard         = document.getElementById('lstmChartCard');
    const featureImportanceCard = document.getElementById('featureImportanceCard');
    const importanceModelSelect = document.getElementById('importanceModelSelect');
    const performanceTableBody  = document.getElementById('performanceTableBody');
    const backtestCard          = document.getElementById('backtestCard');
    const backtestModelSelect   = document.getElementById('backtestModelSelect');
    const runPredictBtn         = document.getElementById('runPredictBtn');
    const predictModelSelect    = document.getElementById('predictModelSelect');
    const runForecastBtn        = document.getElementById('runForecastBtn');

    // Stored backtest data per model (populated after classical training)
    const backtestDataStore = {};

    // ── Plotly Dark Template ─────────────────────────────────────
    const darkLayout = {
        plot_bgcolor:  'rgba(0,0,0,0)',
        paper_bgcolor: 'rgba(0,0,0,0)',
        font: { color: '#f8fafc', family: 'Inter, sans-serif', size: 11 },
        xaxis: { gridcolor: 'rgba(255,255,255,0.05)', linecolor: 'rgba(255,255,255,0.1)', zerolinecolor: 'rgba(255,255,255,0.1)' },
        yaxis: { gridcolor: 'rgba(255,255,255,0.05)', linecolor: 'rgba(255,255,255,0.1)', zerolinecolor: 'rgba(255,255,255,0.1)' }
    };
    const plotConfig = { responsive: true, displayModeBar: false };

    // ── Live Clock ───────────────────────────────────────────────
    const clockEl = document.getElementById('liveClock');
    function tickClock() {
        if (clockEl) {
            const now = new Date();
            clockEl.textContent = now.toLocaleTimeString('en-US', { hour12: false });
        }
    }
    tickClock();
    setInterval(tickClock, 1000);

    // ── Restore symbol from localStorage ────────────────────────
    const storedSymbol = localStorage.getItem('activeStockSymbol');
    if (storedSymbol && Array.from(trainSymbolSelect.options).some(o => o.value === storedSymbol)) {
        trainSymbolSelect.value = storedSymbol;
    }
    const currentSymbol = () => trainSymbolSelect.value;

    // ── Initial load ─────────────────────────────────────────────
    loadLeaderboard(currentSymbol());
    loadFeatureImportance(currentSymbol(), importanceModelSelect.value);
    updateSymbolHUD(currentSymbol());

    // ── Symbol change ────────────────────────────────────────────
    trainSymbolSelect.addEventListener('change', function () {
        localStorage.setItem('activeStockSymbol', this.value);
        lstmChartCard.classList.add('d-none');
        backtestCard.classList.add('d-none');
        loadLeaderboard(this.value);
        loadFeatureImportance(this.value, importanceModelSelect.value);
        updateSymbolHUD(this.value);
        // Reset prediction result
        document.getElementById('predictionResultCard').classList.add('d-none');
    });

    document.getElementById('refreshHudBtn').addEventListener('click', () => updateSymbolHUD(currentSymbol()));
    document.getElementById('refreshLeaderboardBtn').addEventListener('click', () => loadLeaderboard(currentSymbol()));

    importanceModelSelect.addEventListener('change', function () {
        loadFeatureImportance(currentSymbol(), this.value);
    });

    backtestModelSelect.addEventListener('change', function () {
        renderBacktestChart(this.value);
    });

    // ── Live Symbol HUD ──────────────────────────────────────────
    function updateSymbolHUD(symbol) {
        const hud      = document.getElementById('trainSymbolHud');
        const skeleton = document.getElementById('hudSkeleton');
        const closeEl  = document.getElementById('trainClose');
        const changeEl = document.getElementById('trainChange');
        const spanEl   = document.getElementById('trainSpan');
        const rowsEl   = document.getElementById('trainRows');
        const rsiEl    = document.getElementById('hudRsiML');
        const macdEl   = document.getElementById('hudMacdML');
        const volEl    = document.getElementById('hudVolML');

        hud.classList.add('d-none');
        skeleton.classList.remove('d-none');

        fetch(`/api/stock/${symbol}/summary`)
            .then(r => r.json())
            .then(data => {
                skeleton.classList.add('d-none');
                if (!data || data.error) { return; }
                hud.classList.remove('d-none');

                const change    = data.change || 0;
                const pct       = data.pct_change || 0;
                const isUp      = change >= 0;
                closeEl.textContent = `$${data.price.toFixed(2)}`;
                closeEl.style.color = isUp ? '#34d399' : '#f87171';
                changeEl.textContent = `${isUp ? '▲' : '▼'} ${Math.abs(change).toFixed(2)} (${isUp ? '+' : ''}${pct.toFixed(2)}%)`;
                changeEl.style.color  = isUp ? '#34d399' : '#f87171';
                changeEl.title = `Last date: ${data.last_date}`;

                // Fetch full data for span + rows
                fetch(`/api/stock/${symbol}`)
                    .then(r => r.json())
                    .then(full => {
                        if (full.dates) {
                            spanEl.textContent = `${full.dates[0]} → ${full.dates[full.dates.length - 1]}`;
                            rowsEl.textContent = `${full.close.length} rows`;
                        }
                    }).catch(() => {});

                // RSI badge
                if (data.rsi != null) {
                    rsiEl.textContent = `RSI ${data.rsi.toFixed(1)}`;
                    rsiEl.className = 'metric-badge ' + (data.rsi < 30 ? 'badge-bullish' : data.rsi > 70 ? 'badge-bearish' : 'badge-neutral');
                }
                // MACD badge
                if (data.macd != null && data.macd_sig != null) {
                    const isBull = data.macd > data.macd_sig;
                    macdEl.textContent = isBull ? 'MACD Bull' : 'MACD Bear';
                    macdEl.className = 'metric-badge ' + (isBull ? 'badge-bullish' : 'badge-bearish');
                }
                // Volatility badge
                if (data.volatility != null) {
                    volEl.textContent = `Vol ${(data.volatility * 100).toFixed(1)}%`;
                    volEl.className = 'metric-badge ' + (data.volatility > 0.4 ? 'badge-bearish' : 'badge-neutral');
                }
            })
            .catch(() => { skeleton.classList.add('d-none'); });
    }

    // ── One-Click Live Prediction ─────────────────────────────────
    runPredictBtn.addEventListener('click', function () {
        const symbol    = currentSymbol();
        const modelName = predictModelSelect.value;

        runPredictBtn.disabled = true;
        runPredictBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Running…';

        fetch(`/api/predict/${symbol}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ model: modelName })
        })
        .then(r => r.json())
        .then(data => {
            runPredictBtn.disabled = false;
            runPredictBtn.innerHTML = '<i class="bi bi-play-fill me-1"></i>Predict Next Close Price';

            const card = document.getElementById('predictionResultCard');
            if (data.success) {
                card.classList.remove('d-none');
                document.getElementById('predResultPrice').textContent = `$${data.predicted_price.toFixed(4)}`;
                document.getElementById('predResultMeta').textContent  =
                    `${modelName} · Target ${data.prediction_date} · Saved to profile`;
                const conf = Math.min(100, Math.max(0, data.confidence));
                document.getElementById('predConfPct').textContent = `${conf.toFixed(1)}%`;
                setTimeout(() => {
                    document.getElementById('predConfBar').style.width = `${conf}%`;
                }, 60);
                localStorage.setItem('activePredictModel', modelName);
                if (typeof showToast === 'function') showToast(`Prediction saved: $${data.predicted_price.toFixed(2)}`, 'success');
            } else {
                card.classList.add('d-none');
                if (typeof showToast === 'function') showToast('Prediction error: ' + data.error, 'error');
            }
        })
        .catch(err => {
            runPredictBtn.disabled = false;
            runPredictBtn.innerHTML = '<i class="bi bi-play-fill me-1"></i>Predict Next Close Price';
            console.error(err);
        });
    });

    // ── 30-Day LSTM Forecast ──────────────────────────────────────
    if (runForecastBtn) {
        runForecastBtn.addEventListener('click', function () {
            const symbol = currentSymbol();
            runForecastBtn.disabled = true;
            runForecastBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Forecasting…';

            fetch(`/api/forecast/lstm/${symbol}?steps=30`)
                .then(r => r.json())
                .then(data => {
                    runForecastBtn.disabled = false;
                    runForecastBtn.innerHTML = '<i class="bi bi-calendar-week me-1"></i>30-Day Forecast';

                    if (data.success) {
                        const panel = document.getElementById('lstmForecastPanel');
                        panel.classList.remove('d-none');
                        const trace = {
                            x: data.dates,
                            y: data.forecast,
                            mode: 'lines+markers',
                            name: 'Forecast',
                            line: { color: '#10b981', width: 2, dash: 'dot' },
                            marker: { size: 4 },
                            fill: 'tozeroy',
                            fillcolor: 'rgba(16,185,129,0.06)'
                        };
                        const layout = {
                            margin: { t: 10, r: 20, b: 50, l: 60 },
                            xaxis: { title: 'Date', tickangle: -30, ...darkLayout.xaxis },
                            yaxis: { title: 'Price ($)', ...darkLayout.yaxis },
                            ...darkLayout
                        };
                        Plotly.newPlot('plotlyLstmForecastChart', [trace], layout, plotConfig);
                    } else {
                        if (typeof showToast === 'function') showToast('Forecast error: ' + data.error, 'error');
                    }
                })
                .catch(err => {
                    runForecastBtn.disabled = false;
                    runForecastBtn.innerHTML = '<i class="bi bi-calendar-week me-1"></i>30-Day Forecast';
                    console.error(err);
                });
        });
    }

    // ── Terminal Logger ───────────────────────────────────────────
    function terminalLog(bodyId, text, type = 'info') {
        const body = document.getElementById(bodyId);
        if (!body) return;
        const line = document.createElement('div');
        line.className = `terminal-line terminal-${type}`;
        line.textContent = text;
        body.appendChild(line);
        body.scrollTop = body.scrollHeight;
    }

    function terminalClear(bodyId) {
        const body = document.getElementById(bodyId);
        if (body) body.innerHTML = '';
    }

    // ── Train Classical ML ────────────────────────────────────────
    trainClassicalBtn.addEventListener('click', function () {
        const symbol = currentSymbol();

        trainClassicalBtn.disabled = true;
        trainLstmBtn.disabled      = true;
        trainClassicalBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Training…';

        const terminal = document.getElementById('classTerminal');
        terminal.classList.remove('d-none');
        terminalClear('classTerminalBody');

        const steps = [
            [300,  '$ Loading stock data for ' + symbol + '…',          'info'],
            [700,  '$ Extracting lag features + technical indicators…',  'info'],
            [1100, '$ Splitting dataset 80/20 (chronological)…',         'info'],
            [1600, '$ Fitting Linear Regression baseline…',              'info'],
            [2200, '$ Fitting Random Forest (n_estimators=100)…',        'info'],
            [2900, '$ Fitting XGBoost Regressor (lr=0.05)…',             'info'],
            [3200, '$ Serializing models to /models/…',                  'info'],
            [3500, '$ Caching performance metrics to database…',         'info']
        ];
        const bar = document.getElementById('classProgressBar');
        steps.forEach(([delay, msg, type], idx) => {
            setTimeout(() => {
                terminalLog('classTerminalBody', msg, type);
                if (bar) bar.style.width = `${Math.round((idx + 1) / steps.length * 100)}%`;
            }, delay);
        });

        fetch(`/api/train/ml/${symbol}`, { method: 'POST' })
            .then(r => r.json())
            .then(data => {
                trainClassicalBtn.disabled  = false;
                trainLstmBtn.disabled       = false;
                trainClassicalBtn.innerHTML = '<i class="bi bi-play-fill me-1"></i>Train Classical Pipelines';

                if (data.success) {
                    terminalLog('classTerminalBody', '✓ Training complete. All models cached.', 'success');
                    if (bar) bar.style.width = '100%';

                    // Store backtest data
                    if (data.results) {
                        Object.entries(data.results).forEach(([name, res]) => {
                            if (res.test_dates && res.test_actuals && res.test_predictions) {
                                backtestDataStore[name] = res;
                            }
                        });
                    }

                    loadLeaderboard(symbol);
                    loadFeatureImportance(symbol, importanceModelSelect.value);

                    // Show backtest chart if data returned
                    if (data.results && Object.keys(data.results).length > 0) {
                        backtestCard.classList.remove('d-none');
                        renderBacktestChart(backtestModelSelect.value);
                    }

                    // Build performance array for modal
                    const perfs = [];
                    if (data.results) {
                        Object.entries(data.results).forEach(([name, m]) => {
                            perfs.push({ model_name: name, r2: m.r2, mae: m.mae, rmse: m.rmse, mape: m.mape });
                        });
                    } else if (data.performance) {
                        perfs.push(...data.performance);
                    }
                    showTrainingModal('Classical ML', symbol, perfs);
                } else {
                    terminalLog('classTerminalBody', '✗ Error: ' + (data.error || 'Unknown error'), 'error');
                    if (typeof showToast === 'function') showToast('Training failed: ' + data.error, 'error');
                }
            })
            .catch(err => {
                trainClassicalBtn.disabled  = false;
                trainLstmBtn.disabled       = false;
                trainClassicalBtn.innerHTML = '<i class="bi bi-play-fill me-1"></i>Train Classical Pipelines';
                terminalLog('classTerminalBody', '✗ Network error: ' + err.message, 'error');
            });
    });

    // ── Train LSTM ────────────────────────────────────────────────
    trainLstmBtn.addEventListener('click', function () {
        const symbol    = currentSymbol();
        const epochs    = parseInt(lstmEpochs.value) || 5;
        const lookback  = parseInt(lstmLookback.value) || 60;
        const batchSize = lstmBatchSize ? parseInt(lstmBatchSize.value) : 32;

        trainClassicalBtn.disabled  = true;
        trainLstmBtn.disabled       = true;
        trainLstmBtn.innerHTML      = '<span class="spinner-border spinner-border-sm me-2"></span>Training…';
        lstmChartCard.classList.add('d-none');

        const terminal = document.getElementById('lstmTerminal');
        terminal.classList.remove('d-none');
        terminalClear('lstmTerminalBody');

        const epochLabel = document.getElementById('lstmEpochLabel');
        const bar        = document.getElementById('lstmProgressBar');

        const initSteps = [
            [200,  `$ Loading Close price series for ${symbol}…`,              'info'],
            [600,  `$ Fitting MinMaxScaler on training split…`,                 'info'],
            [1000, `$ Building ${lookback}-day sequence windows…`,             'info'],
            [1400, `$ Compiling LSTM model (30×30 units, dropout 0.1)…`,       'info'],
            [1800, `$ Starting training: ${epochs} epochs, batch ${batchSize}…`,'info'],
        ];
        initSteps.forEach(([d, msg, t]) => setTimeout(() => terminalLog('lstmTerminalBody', msg, t), d));

        // Simulate epoch ticks while server trains
        let fakeEpoch = 0;
        const epochInterval = setInterval(() => {
            fakeEpoch++;
            if (fakeEpoch <= epochs) {
                terminalLog('lstmTerminalBody', `  Epoch ${fakeEpoch}/${epochs} — optimizing weights…`, 'info');
                if (epochLabel) epochLabel.textContent = `${fakeEpoch} / ${epochs}`;
                if (bar) bar.style.width = `${Math.round(fakeEpoch / epochs * 100)}%`;
            }
        }, Math.max(400, (epochs * 2200) / epochs));

        fetch(`/api/train/lstm/${symbol}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ epochs, lookback, batch_size: batchSize })
        })
        .then(r => r.json())
        .then(data => {
            clearInterval(epochInterval);
            trainClassicalBtn.disabled  = false;
            trainLstmBtn.disabled       = false;
            trainLstmBtn.innerHTML      = '<i class="bi bi-cpu-fill me-1"></i>Train LSTM Network';
            if (bar) bar.style.width = '100%';

            if (data.success) {
                terminalLog('lstmTerminalBody', `✓ LSTM trained. R²=${data.r2.toFixed(4)} MAE=${data.mae.toFixed(4)}`, 'success');
                loadLeaderboard(symbol);
                renderLossChart(data.loss_history, data.val_loss_history);
                showTrainingModal('LSTM Network', symbol, data.performance ? [data.performance] : [{
                    model_name: 'LSTM',
                    r2: data.r2,
                    mae: data.mae,
                    rmse: data.rmse,
                    mape: data.mape
                }]);
            } else {
                terminalLog('lstmTerminalBody', '✗ Error: ' + (data.error || 'Unknown'), 'error');
                if (typeof showToast === 'function') showToast('LSTM Training failed: ' + data.error, 'error');
            }
        })
        .catch(err => {
            clearInterval(epochInterval);
            trainClassicalBtn.disabled  = false;
            trainLstmBtn.disabled       = false;
            trainLstmBtn.innerHTML      = '<i class="bi bi-cpu-fill me-1"></i>Train LSTM Network';
            terminalLog('lstmTerminalBody', '✗ Network error: ' + err.message, 'error');
        });
    });

    // ── Load Leaderboard ──────────────────────────────────────────
    function loadLeaderboard(symbol) {
        const updatedEl = document.getElementById('leaderboardUpdatedAt');

        fetch(`/api/performance/${symbol}`)
            .then(r => r.json())
            .then(data => {
                if (updatedEl) updatedEl.textContent = 'Updated ' + new Date().toLocaleTimeString();

                if (data.success && data.performance.length > 0) {
                    performanceTableBody.innerHTML = '';
                    data.performance.forEach((p, idx) => {
                        const rankIcon = idx === 0 ? '🥇' : idx === 1 ? '🥈' : idx === 2 ? '🥉' :
                            `<span class="text-muted font-mono" style="font-size:0.78rem;">#${idx + 1}</span>`;
                        const r2Color = p.r2 >= 0.85 ? 'text-success fw-bold' : p.r2 >= 0.5 ? 'text-warning fw-semibold' : 'text-danger';
                        const trainedAt = p.trained_at
                            ? new Date(p.trained_at).toLocaleString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
                            : '—';

                        const row = document.createElement('tr');
                        row.className = idx === 0 ? 'leaderboard-winner animate-fade-in' : '';
                        row.innerHTML = `
                            <td class="fw-semibold text-white">
                                <span class="me-1">${rankIcon}</span>${p.model_name}
                                ${idx === 0 ? '<span class="badge ms-1 py-0" style="background:rgba(251,191,36,0.15);border:1px solid rgba(251,191,36,0.3);color:#fbbf24;font-size:0.62rem;border-radius:4px;">Best</span>' : ''}
                            </td>
                            <td>${p.mae.toFixed(4)}</td>
                            <td>${p.rmse.toFixed(4)}</td>
                            <td class="${r2Color}">${p.r2.toFixed(4)}</td>
                            <td>${p.mape.toFixed(2)}%</td>
                            <td class="text-muted" style="font-size:0.75rem;">${trainedAt}</td>
                        `;
                        performanceTableBody.appendChild(row);
                    });
                } else {
                    performanceTableBody.innerHTML = `
                        <tr><td colspan="6" class="text-center text-secondary py-4" style="font-size:0.85rem;">
                            <i class="bi bi-cpu d-block fs-3 mb-2 text-muted opacity-50"></i>
                            No trained models for ${symbol}. Click Train.
                        </td></tr>`;
                }
            })
            .catch(err => console.error('Leaderboard load error:', err));
    }

    // ── Backtest Chart ────────────────────────────────────────────
    function renderBacktestChart(modelName) {
        const stored = backtestDataStore[modelName];
        if (!stored || !stored.test_dates) { return; }

        const traceActual = {
            x: stored.test_dates,
            y: stored.test_actuals,
            mode: 'lines',
            name: 'Actual',
            line: { color: '#f8fafc', width: 1.5 }
        };
        const tracePred = {
            x: stored.test_dates,
            y: stored.test_predictions,
            mode: 'lines',
            name: `${modelName} Predicted`,
            line: { color: '#3b82f6', width: 2, dash: 'dot' }
        };
        const layout = {
            margin: { t: 10, r: 20, b: 50, l: 60 },
            xaxis: { title: 'Date', tickangle: -30, nticks: 8, ...darkLayout.xaxis },
            yaxis: { title: 'Price ($)', ...darkLayout.yaxis },
            legend: { orientation: 'h', y: 1.08, x: 0 },
            ...darkLayout
        };
        Plotly.newPlot('plotlyBacktestChart', [traceActual, tracePred], layout, plotConfig);
    }

    // ── LSTM Loss Chart ───────────────────────────────────────────
    function renderLossChart(losses, valLosses) {
        lstmChartCard.classList.remove('d-none');
        document.getElementById('lstmForecastPanel').classList.add('d-none');

        const x = Array.from({ length: losses.length }, (_, i) => i + 1);
        const traces = [
            { x, y: losses,    mode: 'lines+markers', name: 'Train Loss',  line: { color: '#3b82f6', width: 2 }, marker: { size: 5 } },
            { x, y: valLosses, mode: 'lines+markers', name: 'Val Loss',    line: { color: '#10b981', width: 2 }, marker: { size: 5 } }
        ];
        const layout = {
            margin: { t: 10, r: 20, b: 40, l: 60 },
            xaxis: { title: 'Epoch', dtick: 1, ...darkLayout.xaxis },
            yaxis: { title: 'MSE Loss', ...darkLayout.yaxis },
            legend: { orientation: 'h', y: 1.1, x: 0 },
            ...darkLayout
        };
        Plotly.newPlot('plotlyLstmLossChart', traces, layout, plotConfig);
    }

    // ── Feature Importance ────────────────────────────────────────
    function loadFeatureImportance(symbol, model) {
        fetch(`/api/feature_importance/${symbol}?model=${encodeURIComponent(model)}`)
            .then(r => r.json())
            .then(data => {
                if (data.success && data.features.length > 0) {
                    featureImportanceCard.classList.remove('d-none');
                    const sorted = [...data.features].reverse();
                    const colors = sorted.map((_, i) => `rgba(16,185,129,${0.35 + i / sorted.length * 0.65})`);
                    const trace = {
                        x: sorted.map(f => f.importance),
                        y: sorted.map(f => f.name),
                        type: 'bar', orientation: 'h',
                        marker: { color: colors, line: { color: '#10b981', width: 1 } }
                    };
                    const layout = {
                        margin: { t: 10, r: 20, b: 30, l: 160 },
                        xaxis: { title: 'Importance', ...darkLayout.xaxis },
                        yaxis: { ...darkLayout.yaxis },
                        ...darkLayout
                    };
                    Plotly.newPlot('plotlyFeatureImportanceChart', [trace], layout, plotConfig);
                } else {
                    featureImportanceCard.classList.add('d-none');
                }
            })
            .catch(() => featureImportanceCard.classList.add('d-none'));
    }

    // ── Post-Training Success Modal ───────────────────────────────
    function showTrainingModal(modelType, symbol, performances) {
        const modalEl = document.getElementById('trainingSuccessModal');
        if (!modalEl) return;

        document.getElementById('trainingModalTitle').textContent    = `${modelType} Training Complete`;
        document.getElementById('trainingModalSubtitle').textContent = `${symbol} — models cached to database`;

        const pillsEl = document.getElementById('trainingMetricPills');
        pillsEl.innerHTML = '';

        if (performances && performances.length > 0) {
            const best = performances.reduce((a, b) => (a.r2 > b.r2 ? a : b));
            performances.forEach(p => {
                const col = p.r2 >= 0.85 ? '#34d399' : p.r2 >= 0.6 ? '#fbbf24' : '#f87171';
                const pill = document.createElement('div');
                pill.className = 'metric-pill';
                pill.innerHTML = `
                    <span class="pill-label">${p.model_name}</span>
                    <span class="pill-value" style="color:${col}">R² ${p.r2.toFixed(3)}</span>
                    <span class="pill-sub">MAE ${p.mae.toFixed(2)}</span>
                `;
                pillsEl.appendChild(pill);
            });
            const bestBox = document.getElementById('bestModelBox');
            bestBox.classList.remove('d-none');
            document.getElementById('bestModelName').textContent  = best.model_name;
            document.getElementById('bestModelScore').textContent = `R² ${best.r2.toFixed(4)} · RMSE ${best.rmse.toFixed(4)}`;
        } else {
            pillsEl.innerHTML = '<span class="text-muted" style="font-size:0.83rem;">No metric data returned.</span>';
            document.getElementById('bestModelBox').classList.add('d-none');
        }

        new bootstrap.Modal(modalEl).show();
    }
});
