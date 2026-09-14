/**
 * Frontend Chart Renderer & State Manager v2.0
 * Handles data fetching, time range filtering, UI metrics binding, and Plotly layouts
 */

// Global raw data cache for time-range filtering without re-fetch
let _cachedStockData = null;
let _activeRangeDays = 365; // default 1Y

// Helper to count up/down numbers with premium styling glow triggers
function animateNumber(element, targetVal, decimalPlaces = 2, prefix = '', suffix = '') {
    const rawText = element.innerText.replace(/[^0-9.-]/g, '');
    const startVal = parseFloat(rawText) || 0;
    const duration = 750; // ms
    let startTimestamp = null;
    
    // Add glowing transition effect
    const diff = targetVal - startVal;
    if (Math.abs(diff) > 0.0001) {
        if (diff > 0) {
            element.classList.add('metric-glow-green');
            setTimeout(() => element.classList.remove('metric-glow-green'), 800);
        } else {
            element.classList.add('metric-glow-red');
            setTimeout(() => element.classList.remove('metric-glow-red'), 800);
        }
    }

    const step = (timestamp) => {
        if (!startTimestamp) startTimestamp = timestamp;
        const progress = Math.min((timestamp - startTimestamp) / duration, 1);
        const currentVal = startVal + progress * (targetVal - startVal);
        element.innerText = prefix + currentVal.toFixed(decimalPlaces) + suffix;
        if (progress < 1) {
            window.requestAnimationFrame(step);
        } else {
            element.innerText = prefix + targetVal.toFixed(decimalPlaces) + suffix;
        }
    };
    window.requestAnimationFrame(step);
}

document.addEventListener('DOMContentLoaded', function() {
    const symbolSelect = document.getElementById('symbolSelect');
    const downloadReportBtn = document.getElementById('downloadReportBtn');

    // ── Time Range Filter Buttons ──
    document.querySelectorAll('.time-range-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            document.querySelectorAll('.time-range-btn').forEach(b => b.classList.remove('active'));
            this.classList.add('active');
            _activeRangeDays = parseInt(this.getAttribute('data-range')) || 0;
            if (_cachedStockData) {
                const filtered = filterDataByRange(_cachedStockData, _activeRangeDays);
                updateDashboardMetrics(filtered);
                renderPriceChart(filtered);
                renderIndicatorChart(filtered);
                renderVolumeChart(filtered);
                updateLastUpdateLabel(filtered);
            }
        });
    });
    
    // Prediction DOM elements
    const predictBtn = document.getElementById('predictBtn');
    const predictModelSelect = document.getElementById('predictModelSelect');
    const predictionResultBox = document.getElementById('predictionResultBox');
    const predTargetDate = document.getElementById('predTargetDate');
    const predPriceVal = document.getElementById('predPriceVal');
    const predConfVal = document.getElementById('predConfVal');

    // Sync predictModelSelect selection to localStorage
    if (predictModelSelect) {
        localStorage.setItem('activePredictModel', predictModelSelect.value);
        predictModelSelect.addEventListener('change', function() {
            localStorage.setItem('activePredictModel', this.value);
        });
    }

    // Initialize Bootstrap Tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Fix Plotly resize glitch when switching Bootstrap tabs
    const tabs = document.querySelectorAll('button[data-bs-toggle="tab"]');
    tabs.forEach(tab => {
        tab.addEventListener('shown.bs.tab', function (event) {
            const targetId = event.target.getAttribute('data-bs-target');
            let chartId = '';
            if (targetId === '#candles') chartId = 'plotlyPriceChart';
            else if (targetId === '#indicators') chartId = 'plotlyIndicatorChart';
            else if (targetId === '#volume') chartId = 'plotlyVolumeChart';
            
            if (chartId) {
                const container = document.getElementById(chartId);
                if (container && container.classList.contains('js-plotly-plot')) {
                    Plotly.Plots.resize(container);
                }
            }
        });
    });

    // Helper to dynamically adjust Plotly layout parameters to the selected visual theme
    function getPlotlyTemplate() {
        const activeTheme = localStorage.getItem('selectedTheme') || 'dark';
        let fontColor = '#f8fafc';
        let gridColor = 'rgba(255, 255, 255, 0.05)';
        let lineColor = 'rgba(255, 255, 255, 0.1)';
        
        if (activeTheme === 'light') {
            fontColor = '#0f172a';
            gridColor = 'rgba(15, 23, 42, 0.06)';
            lineColor = 'rgba(15, 23, 42, 0.12)';
        } else if (activeTheme === 'cyberpunk') {
            fontColor = '#00ffff';
            gridColor = 'rgba(255, 0, 255, 0.1)';
            lineColor = 'rgba(255, 0, 255, 0.2)';
        } else if (activeTheme === 'forest') {
            fontColor = '#ecfdf5';
            gridColor = 'rgba(16, 185, 129, 0.05)';
            lineColor = 'rgba(16, 185, 129, 0.15)';
        }
        
        return {
            layout: {
                plot_bgcolor: 'rgba(0,0,0,0)',
                paper_bgcolor: 'rgba(0,0,0,0)',
                font: { color: fontColor, family: 'Inter, sans-serif' },
                xaxis: {
                    gridcolor: gridColor,
                    linecolor: lineColor,
                    zerolinecolor: lineColor
                },
                yaxis: {
                    gridcolor: gridColor,
                    linecolor: lineColor,
                    zerolinecolor: lineColor
                }
            }
        };
    }

    // Listen to themeChanged custom event to adjust charts dynamically
    window.addEventListener('themeChanged', function(e) {
        loadStockData(symbolSelect.value);
    });

    // Load selected stock on page load (synchronized with other workspace panels)
    const storedSymbol = localStorage.getItem('activeStockSymbol');
    if (storedSymbol && Array.from(symbolSelect.options).some(opt => opt.value === storedSymbol)) {
        symbolSelect.value = storedSymbol;
    }
    loadStockData(symbolSelect.value);
    downloadReportBtn.setAttribute('href', `/report/download/${symbolSelect.value}`);

    // Update dashboard symbol label
    const dashSymbolLabel = document.getElementById('dashSymbolLabel');
    if (dashSymbolLabel) dashSymbolLabel.textContent = symbolSelect.value;

    // Bind event change on stock selection selector
    symbolSelect.addEventListener('change', function(e) {
        const symbol = e.target.value;
        localStorage.setItem('activeStockSymbol', symbol);

        // Update status label
        if (dashSymbolLabel) dashSymbolLabel.textContent = symbol;

        // Hide previous prediction box
        predictionResultBox.classList.add('d-none');

        // Update PDF report download link
        downloadReportBtn.setAttribute('href', `/report/download/${symbol}`);

        // Load data
        loadStockData(symbol);
    });

    // Bind predict event trigger with smooth step animation transitions
    predictBtn.addEventListener('click', function() {
        const symbol = symbolSelect.value;
        const model = predictModelSelect.value;
        
        predictBtn.disabled = true;
        
        // Progressive prediction step updates
        const steps = [
            "Preprocessing history...",
            "Scaling technical parameters...",
            "Running model inference...",
            "Validating error score...",
            "Finalizing prediction..."
        ];
        let currentStep = 0;
        predictBtn.innerHTML = `<span class="spinner-border spinner-border-sm me-1" role="status" aria-hidden="true"></span> ${steps[0]}`;
        
        const stepInterval = setInterval(() => {
            currentStep++;
            if (currentStep < steps.length) {
                predictBtn.innerHTML = `<span class="spinner-border spinner-border-sm me-1" role="status" aria-hidden="true"></span> ${steps[currentStep]}`;
            } else {
                clearInterval(stepInterval);
            }
        }, 600);
        
        fetch(`/api/predict/${symbol}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ model: model })
        })
        .then(response => response.json())
        .then(data => {
            clearInterval(stepInterval);
            predictBtn.disabled = false;
            predictBtn.innerHTML = `<i class="bi bi-lightning-charge me-1"></i>Generate Prediction`;
            
            if (data.success) {
                predTargetDate.innerText = data.prediction_date;
                predPriceVal.innerText = `$${data.predicted_price.toFixed(2)}`;
                predConfVal.innerText = `${data.confidence.toFixed(1)}%`;
                
                // Style confidence color
                if (data.confidence > 80) {
                    predConfVal.className = 'text-success fw-bold';
                } else if (data.confidence > 60) {
                    predConfVal.className = 'text-warning fw-bold';
                } else {
                    predConfVal.className = 'text-danger fw-bold';
                }
                
                // Smoothly show prediction result box
                predictionResultBox.classList.remove('d-none');
                predictionResultBox.classList.remove('animate-fade-in');
                void predictionResultBox.offsetWidth; // Trigger reflow for animation
                predictionResultBox.classList.add('animate-fade-in');
            } else {
                alert("Prediction Error: " + data.error);
            }
        })
        .catch(err => {
            clearInterval(stepInterval);
            predictBtn.disabled = false;
            predictBtn.innerHTML = `<i class="bi bi-lightning-charge me-1"></i>Generate Prediction`;
            console.error("Prediction fetch failed", err);
        });
    });

    function loadStockHeatmap(symbol) {
        const activeTheme = localStorage.getItem('selectedTheme') || 'dark';
        const imgEl = document.getElementById('seabornHeatmapImg');
        const loaderEl = document.getElementById('heatmapLoader');
        const errorEl = document.getElementById('heatmapError');
        
        if (errorEl) errorEl.classList.add('d-none');
        
        if (imgEl && loaderEl) {
            imgEl.style.display = 'none';
            loaderEl.style.display = 'inline-block';
            
            fetch(`/api/stock/${symbol}/heatmap?theme=${activeTheme}`)
            .then(res => {
                if (!res.ok) {
                    throw new Error(`Server returned status ${res.status}`);
                }
                return res.json();
            })
            .then(data => {
                loaderEl.style.display = 'none';
                if (data.success && data.image) {
                    imgEl.src = `data:image/png;base64,${data.image}`;
                    imgEl.style.display = 'block';
                } else {
                    if (errorEl) {
                        errorEl.innerText = data.error || "Failed to load heatmap";
                        errorEl.classList.remove('d-none');
                    }
                }
            })
            .catch(err => {
                console.error("Heatmap fetch error:", err);
                loaderEl.style.display = 'none';
                if (errorEl) {
                    errorEl.innerText = "Error loading heatmap visualization.";
                    errorEl.classList.remove('d-none');
                }
            });
        }
    }

    // Whether to show Bollinger Bands overlay (toggled by .bb-toggle-btn)
    let _showBBands = false;

    function filterDataByRange(data, days) {
        if (!days || days === 0) return data; // 'All'
        const cutoff = new Date();
        cutoff.setDate(cutoff.getDate() - days);
        const cutoffStr = cutoff.toISOString().slice(0, 10);

        const idx = data.dates.findIndex(d => d >= cutoffStr);
        if (idx <= 0) return data;

        const slice = (arr) => Array.isArray(arr) ? arr.slice(idx) : arr;
        return {
            dates:       slice(data.dates),
            open:        slice(data.open),
            high:        slice(data.high),
            low:         slice(data.low),
            close:       slice(data.close),
            volume:      slice(data.volume),
            sma20:       slice(data.sma20),
            sma50:       slice(data.sma50),
            sma200:      slice(data.sma200),
            macd:        slice(data.macd),
            macd_signal: slice(data.macd_signal),
            macd_hist:   slice(data.macd_hist),
            rsi:         slice(data.rsi),
            volatility:  slice(data.volatility),
            bb_upper:    slice(data.bb_upper),
            bb_mid:      slice(data.bb_mid),
            bb_lower:    slice(data.bb_lower)
        };
    }

    function updateLastUpdateLabel(data) {
        const el = document.getElementById('dashLastUpdate');
        if (el && data.dates && data.dates.length > 0) {
            el.textContent = `Last: ${data.dates[data.dates.length - 1]}`;
        }
    }

    function loadStockData(symbol) {
        // Update Chart Title Header
        document.getElementById('chartHeaderTitle').innerHTML =
            `<i class="bi bi-graph-up me-2 text-primary"></i>Historical Analysis — ${symbol}`;

        // Fetch Seaborn correlation heatmap
        loadStockHeatmap(symbol);

        // Add skeleton state to metric cards
        document.querySelectorAll('.metric-value-update').forEach(el => {
            el.innerHTML = '<span class="text-muted">—</span>';
        });

        fetch(`/api/stock/${symbol}`)
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                console.error("Stock data error:", data.error);
                return;
            }

            // Cache full data
            _cachedStockData = data;

            // Apply active range filter
            const filtered = filterDataByRange(data, _activeRangeDays);

            // 1. Bind Dashboard Metrics
            updateDashboardMetrics(filtered);

            // 2. Render Plots
            renderPriceChart(filtered);
            renderIndicatorChart(filtered);
            renderVolumeChart(filtered);
            updateLastUpdateLabel(filtered);
        })
        .catch(err => console.error("Error loading stock data API", err));

        // Fetch AI News & Sentiment
        fetch(`/api/sentiment/${symbol}`)
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                console.error("Sentiment load error:", data.error);
                return;
            }
            
            // Bind overall signal
            const signalBadge = document.getElementById('sentimentSignalBadge');
            signalBadge.innerText = data.signal;
            if (data.signal === 'Bullish') {
                signalBadge.className = 'metric-badge badge-bullish';
            } else if (data.signal === 'Bearish') {
                signalBadge.className = 'metric-badge badge-bearish';
            } else {
                signalBadge.className = 'metric-badge badge-neutral';
            }
            
            // Bind sentiment score val
            document.getElementById('sentimentScoreVal').innerText = data.sentiment_score.toFixed(2);
            
            // Map score from [-1, 1] to percentage [0, 100] for progress bar
            const percent = ((data.sentiment_score + 1) / 2) * 100;
            const progressBar = document.getElementById('sentimentProgressBar');
            progressBar.style.width = `${percent}%`;
            progressBar.setAttribute('aria-valuenow', percent);
            
            // Render news list
            const newsList = document.getElementById('sentimentNewsList');
            newsList.innerHTML = '';
            
            // Clear any previously selected headline details
            const selectedNewsCard = document.getElementById('selectedNewsCard');
            if (selectedNewsCard) selectedNewsCard.classList.add('d-none');
            
            data.headlines.forEach(hl => {
                let badgeClass = 'badge-neutral';
                if (hl.type === 'Positive') badgeClass = 'badge-bullish';
                else if (hl.type === 'Negative') badgeClass = 'badge-bearish';
                
                // Escape single quotes to prevent JavaScript parse errors
                const escapedText = hl.text.replace(/'/g, "\\'");
                
                const item = `
                    <div class="p-3 mb-2 rounded text-start headline-item" onclick="selectNewsHeadline(this, '${escapedText}')" style="background: rgba(255, 255, 255, 0.03); border: 1px solid rgba(255, 255, 255, 0.06); cursor: pointer; transition: all 0.2s ease;">
                        <div class="text-white mb-2" style="font-size: 0.85rem; line-height: 1.4; font-weight: 500;">${hl.text}</div>
                        <div class="d-flex justify-content-between align-items-center">
                            <span class="metric-badge metric-badge-sm ${badgeClass}">${hl.type} Headline</span>
                            <span class="font-monospace" style="font-size: 0.75rem; color: #cbd5e1;">Score: ${hl.score >= 0 ? '+' : ''}${hl.score.toFixed(2)}</span>
                        </div>
                    </div>
                `;
                newsList.innerHTML += item;
            });
        })
        .catch(err => console.error("Error loading sentiment API:", err));
    }

    function updateDashboardMetrics(data) {
        const prices = data.close;
        const dates = data.dates;
        const rsi = data.rsi;
        const macd = data.macd;
        const macdSig = data.macd_signal;
        const vols = data.volatility;

        const latestPrice = prices[prices.length - 1];
        const prevPrice = prices[prices.length - 2];
        const priceChange = latestPrice - prevPrice;
        const pctChange = (priceChange / prevPrice) * 100;

        // Price elements
        const priceText = document.getElementById('metricPrice');
        const priceChangeText = document.getElementById('metricPriceChange');
        animateNumber(priceText, latestPrice, 2, '$', '');
        priceChangeText.innerText = `${priceChange >= 0 ? '+' : ''}${priceChange.toFixed(2)} (${priceChange >= 0 ? '+' : ''}${pctChange.toFixed(2)}%)`;
        priceChangeText.className = priceChange >= 0 ? 'small text-success fw-semibold' : 'small text-danger fw-semibold';

        // RSI elements
        const rsiVal = rsi[rsi.length - 1];
        const rsiText = document.getElementById('metricRsi');
        const rsiBadge = document.getElementById('metricRsiBadge');
        animateNumber(rsiText, rsiVal, 2, '', '');
        
        if (rsiVal < 30) {
            rsiBadge.innerText = 'Oversold';
            rsiBadge.className = 'metric-badge badge-bullish';
        } else if (rsiVal > 70) {
            rsiBadge.innerText = 'Overbought';
            rsiBadge.className = 'metric-badge badge-bearish';
        } else {
            rsiBadge.innerText = 'Neutral';
            rsiBadge.className = 'metric-badge badge-neutral';
        }

        // MACD elements
        const lastMacd = macd[macd.length - 1];
        const lastMacdSig = macdSig[macdSig.length - 1];
        const macdText = document.getElementById('metricMacd');
        const macdBadge = document.getElementById('metricMacdBadge');
        animateNumber(macdText, lastMacd, 4, '', '');
        
        if (lastMacd > lastMacdSig) {
            macdBadge.innerText = 'Bullish Cross';
            macdBadge.className = 'metric-badge badge-bullish';
        } else {
            macdBadge.innerText = 'Bearish Cross';
            macdBadge.className = 'metric-badge badge-bearish';
        }

        // Volatility elements
        const lastVol = vols[vols.length - 1];
        const volText = document.getElementById('metricVol');
        animateNumber(volText, lastVol * 100, 1, '', '%');

        // Update Technical consensus Signals Table cells
        const lastSma20 = data.sma20[data.sma20.length - 1];
        const lastSma50 = data.sma50[data.sma50.length - 1];
        
        // SMA 20 Row
        const sigSma20 = document.getElementById('sigSma20');
        const sigSma20Badge = document.getElementById('sigSma20Badge');
        const sigSma20Action = document.getElementById('sigSma20Action');
        if (sigSma20 && sigSma20Badge && sigSma20Action) {
            sigSma20.innerText = `$${lastSma20.toFixed(2)}`;
            if (latestPrice > lastSma20) {
                sigSma20Badge.innerText = 'Bullish';
                sigSma20Badge.className = 'metric-badge metric-badge-sm badge-bullish';
                sigSma20Action.innerText = 'Supportive / Accumulate';
            } else {
                sigSma20Badge.innerText = 'Bearish';
                sigSma20Badge.className = 'metric-badge metric-badge-sm badge-bearish';
                sigSma20Action.innerText = 'Resistance / Trimming';
            }
        }

        // SMA 50 Row
        const sigSma50 = document.getElementById('sigSma50');
        const sigSma50Badge = document.getElementById('sigSma50Badge');
        const sigSma50Action = document.getElementById('sigSma50Action');
        if (sigSma50 && sigSma50Badge && sigSma50Action) {
            sigSma50.innerText = `$${lastSma50.toFixed(2)}`;
            if (latestPrice > lastSma50) {
                sigSma50Badge.innerText = 'Bullish';
                sigSma50Badge.className = 'metric-badge metric-badge-sm badge-bullish';
                sigSma50Action.innerText = 'Bullish Trend / Hold';
            } else {
                sigSma50Badge.innerText = 'Bearish';
                sigSma50Badge.className = 'metric-badge metric-badge-sm badge-bearish';
                sigSma50Action.innerText = 'Bearish Trend / Avoid';
            }
        }

        // RSI Row
        const sigRsi = document.getElementById('sigRsi');
        const sigRsiBadge = document.getElementById('sigRsiBadge');
        const sigRsiAction = document.getElementById('sigRsiAction');
        if (sigRsi && sigRsiBadge && sigRsiAction) {
            sigRsi.innerText = rsiVal.toFixed(2);
            if (rsiVal < 30) {
                sigRsiBadge.innerText = 'Bullish';
                sigRsiBadge.className = 'metric-badge metric-badge-sm badge-bullish';
                sigRsiAction.innerText = 'Oversold / Reversal Buy';
            } else if (rsiVal > 70) {
                sigRsiBadge.innerText = 'Bearish';
                sigRsiBadge.className = 'metric-badge metric-badge-sm badge-bearish';
                sigRsiAction.innerText = 'Overbought / Reversal Sell';
            } else {
                sigRsiBadge.innerText = 'Neutral';
                sigRsiBadge.className = 'metric-badge metric-badge-sm badge-neutral';
                sigRsiAction.innerText = 'Consolidation / Hold';
            }
        }

        // MACD Row
        const sigMacd = document.getElementById('sigMacd');
        const sigMacdBadge = document.getElementById('sigMacdBadge');
        const sigMacdAction = document.getElementById('sigMacdAction');
        if (sigMacd && sigMacdBadge && sigMacdAction) {
            sigMacd.innerText = lastMacd.toFixed(4);
            if (lastMacd > lastMacdSig) {
                sigMacdBadge.innerText = 'Bullish';
                sigMacdBadge.className = 'metric-badge metric-badge-sm badge-bullish';
                sigMacdAction.innerText = 'Bullish Cross / Momentum';
            } else {
                sigMacdBadge.innerText = 'Bearish';
                sigMacdBadge.className = 'metric-badge metric-badge-sm badge-bearish';
                sigMacdAction.innerText = 'Bearish Cross / Sell';
            }
        }

        // Volatility Row
        const sigVol = document.getElementById('sigVol');
        const sigVolBadge = document.getElementById('sigVolBadge');
        const sigVolAction = document.getElementById('sigVolAction');
        if (sigVol && sigVolBadge && sigVolAction) {
            sigVol.innerText = `${(lastVol * 100).toFixed(1)}%`;
            if (lastVol > 0.03) {
                sigVolBadge.innerText = 'Neutral';
                sigVolBadge.className = 'metric-badge metric-badge-sm badge-neutral';
                sigVolAction.innerText = 'High Risk / Hedging recommended';
            } else {
                sigVolBadge.innerText = 'Bullish';
                sigVolBadge.className = 'metric-badge metric-badge-sm badge-bullish';
                sigVolAction.innerText = 'Low Risk / Stable accumulation';
            }
        }
    }

    // Wire BB toggle button
    document.addEventListener('click', function(e) {
        const btn = e.target.closest('.bb-toggle-btn');
        if (!btn) return;
        _showBBands = !_showBBands;
        btn.classList.toggle('active', _showBBands);
        btn.innerHTML = _showBBands
            ? '<i class="bi bi-toggles me-1"></i>BB On'
            : '<i class="bi bi-toggles me-1"></i>BB';
        if (_cachedStockData) {
            const filtered = filterDataByRange(_cachedStockData, _activeRangeDays);
            renderPriceChart(filtered);
        }
    });

    function renderPriceChart(data) {
        const traceCandles = {
            x: data.dates,
            close: data.close,
            decrease: { line: { color: '#f87171' }, fillcolor: 'rgba(248,113,113,0.7)' },
            high: data.high,
            increase: { line: { color: '#34d399' }, fillcolor: 'rgba(52,211,153,0.7)' },
            low: data.low,
            open: data.open,
            type: 'candlestick',
            name: 'Price',
            yaxis: 'y',
            hoverinfo: 'x+y'
        };

        const traceSma20 = {
            x: data.dates,
            y: data.sma20,
            type: 'scatter',
            mode: 'lines',
            line: { color: '#3b82f6', width: 1.5 },
            name: 'SMA 20',
            hovertemplate: 'SMA 20: $%{y:.2f}<extra></extra>'
        };

        const traceSma50 = {
            x: data.dates,
            y: data.sma50,
            type: 'scatter',
            mode: 'lines',
            line: { color: '#8b5cf6', width: 1.5 },
            name: 'SMA 50',
            hovertemplate: 'SMA 50: $%{y:.2f}<extra></extra>'
        };

        const traceSma200 = {
            x: data.dates,
            y: data.sma200,
            type: 'scatter',
            mode: 'lines',
            line: { color: '#f59e0b', width: 1.5, dash: 'dot' },
            name: 'SMA 200',
            hovertemplate: 'SMA 200: $%{y:.2f}<extra></extra>'
        };

        const plotData = [traceCandles, traceSma20, traceSma50, traceSma200];

        // Bollinger Bands overlay
        if (_showBBands && data.bb_upper && data.bb_lower) {
            // Shaded fill between upper and lower
            plotData.push({
                x: [...data.dates, ...data.dates.slice().reverse()],
                y: [...data.bb_upper, ...data.bb_lower.slice().reverse()],
                fill: 'toself',
                fillcolor: 'rgba(99,102,241,0.07)',
                line: { color: 'transparent' },
                type: 'scatter',
                mode: 'lines',
                name: 'BB Band',
                showlegend: false,
                hoverinfo: 'skip'
            });
            plotData.push({
                x: data.dates,
                y: data.bb_upper,
                type: 'scatter',
                mode: 'lines',
                line: { color: 'rgba(99,102,241,0.55)', width: 1, dash: 'dash' },
                name: 'BB Upper',
                hovertemplate: 'BB Upper: $%{y:.2f}<extra></extra>'
            });
            plotData.push({
                x: data.dates,
                y: data.bb_mid,
                type: 'scatter',
                mode: 'lines',
                line: { color: 'rgba(99,102,241,0.8)', width: 1 },
                name: 'BB Mid',
                hovertemplate: 'BB Mid: $%{y:.2f}<extra></extra>'
            });
            plotData.push({
                x: data.dates,
                y: data.bb_lower,
                type: 'scatter',
                mode: 'lines',
                line: { color: 'rgba(99,102,241,0.55)', width: 1, dash: 'dash' },
                name: 'BB Lower',
                hovertemplate: 'BB Lower: $%{y:.2f}<extra></extra>'
            });
        }

        const currentTemplate = getPlotlyTemplate();
        const layout = {
            margin: { t: 30, r: 20, b: 40, l: 60 },
            xaxis: {
                rangeslider: { visible: false },
                type: 'date',
                showspikes: true,
                spikemode: 'across',
                spikesnap: 'cursor',
                spikecolor: 'rgba(255,255,255,0.2)',
                spikedash: 'dot',
                spikethickness: 1,
                ...currentTemplate.layout.xaxis
            },
            yaxis: {
                title: { text: 'Price ($)', font: { size: 11 } },
                autorange: true,
                showspikes: true,
                spikemode: 'across',
                spikesnap: 'cursor',
                spikecolor: 'rgba(255,255,255,0.2)',
                spikedash: 'dot',
                spikethickness: 1,
                tickprefix: '$',
                ...currentTemplate.layout.yaxis
            },
            legend: { orientation: 'h', y: 1.08, x: 0, font: { size: 11 } },
            hovermode: 'x unified',
            hoverlabel: {
                bgcolor: 'rgba(15,23,42,0.92)',
                bordercolor: 'rgba(99,102,241,0.4)',
                font: { color: '#f8fafc', size: 12, family: 'JetBrains Mono, monospace' }
            },
            ...currentTemplate.layout
        };

        Plotly.newPlot('plotlyPriceChart', plotData, layout, {
            responsive: true,
            displayModeBar: true,
            displaylogo: false,
            modeBarButtonsToRemove: ['select2d', 'lasso2d', 'autoScale2d', 'hoverClosestCartesian', 'hoverCompareCartesian'],
            toImageButtonOptions: { format: 'png', scale: 2 }
        });
    }

    function renderIndicatorChart(data) {
        // Multi-chart stacked layout
        const traceMacd = {
            x: data.dates,
            y: data.macd,
            type: 'scatter',
            mode: 'lines',
            line: { color: '#60a5fa', width: 1.5 },
            name: 'MACD',
            xaxis: 'x',
            yaxis: 'y2'
        };

        const traceSignal = {
            x: data.dates,
            y: data.macd_signal,
            type: 'scatter',
            mode: 'lines',
            line: { color: '#fb923c', width: 1.5 },
            name: 'Signal Line',
            xaxis: 'x',
            yaxis: 'y2'
        };

        const histColors = data.macd_hist.map(v => v >= 0 ? '#34d399' : '#f87171');
        const traceHist = {
            x: data.dates,
            y: data.macd_hist,
            type: 'bar',
            marker: { color: histColors },
            name: 'Histogram',
            xaxis: 'x',
            yaxis: 'y2'
        };

        const traceRsi = {
            x: data.dates,
            y: data.rsi,
            type: 'scatter',
            mode: 'lines',
            line: { color: '#a78bfa', width: 1.5 },
            name: 'RSI (14)',
            xaxis: 'x',
            yaxis: 'y'
        };

        // Horizontal thresholds for RSI (30 and 70)
        const line70 = {
            x: [data.dates[0], data.dates[data.dates.length-1]],
            y: [70, 70],
            type: 'scatter',
            mode: 'lines',
            line: { color: '#f87171', width: 1, dash: 'dash' },
            name: 'Overbought (70)',
            showlegend: false
        };

        const line30 = {
            x: [data.dates[0], data.dates[data.dates.length-1]],
            y: [30, 30],
            type: 'scatter',
            mode: 'lines',
            line: { color: '#34d399', width: 1, dash: 'dash' },
            name: 'Oversold (30)',
            showlegend: false
        };

        const plotData = [traceMacd, traceSignal, traceHist, traceRsi, line70, line30];

        const currentTemplate = getPlotlyTemplate();
        const layout = {
            grid: { rows: 2, columns: 1, pattern: 'independent' },
            margin: { t: 30, r: 30, b: 30, l: 50 },
            xaxis: {
                type: 'date',
                ...currentTemplate.layout.xaxis
            },
            yaxis: {
                title: 'RSI Value',
                range: [0, 100],
                domain: [0, 0.45],
                ...currentTemplate.layout.yaxis
            },
            yaxis2: {
                title: 'MACD',
                domain: [0.55, 1],
                ...currentTemplate.layout.yaxis
            },
            legend: { orientation: 'h', y: 1.1, x: 0 },
            ...currentTemplate.layout
        };

        Plotly.newPlot('plotlyIndicatorChart', plotData, layout, { responsive: true, displayModeBar: false });
    }

    function renderVolumeChart(data) {
        // Color based on positive/negative close difference
        const volumeColors = [];
        for (let i = 0; i < data.close.length; i++) {
            if (i === 0) {
                volumeColors.push('#34d399');
            } else {
                volumeColors.push(data.close[i] >= data.close[i - 1] ? '#34d399' : '#f87171');
            }
        }

        const traceVolume = {
            x: data.dates,
            y: data.volume,
            type: 'bar',
            marker: { color: volumeColors },
            name: 'Volume'
        };

        const currentTemplate = getPlotlyTemplate();
        const layout = {
            margin: { t: 30, r: 30, b: 30, l: 50 },
            xaxis: {
                type: 'date',
                ...currentTemplate.layout.xaxis
            },
            yaxis: {
                title: 'Shares Traded',
                ...currentTemplate.layout.yaxis
            },
            legend: { orientation: 'h', y: 1.1, x: 0 },
            ...currentTemplate.layout
        };

        Plotly.newPlot('plotlyVolumeChart', [traceVolume], layout, { responsive: true, displayModeBar: false });
    }
});

// Expose news selection and AI analysis globally
window.selectNewsHeadline = function(el, text) {
    // Un-highlight previous headlines
    document.querySelectorAll('#sentimentNewsList > div').forEach(div => {
        div.style.background = 'rgba(255, 255, 255, 0.03)';
        div.style.borderColor = 'rgba(255, 255, 255, 0.06)';
    });
    
    // Highlight clicked headline
    el.style.background = 'rgba(59, 130, 246, 0.08)';
    el.style.borderColor = 'rgba(59, 130, 246, 0.3)';
    
    // Update analyzer card
    const card = document.getElementById('selectedNewsCard');
    const textEl = document.getElementById('selectedNewsText');
    if (card && textEl) {
        textEl.innerText = `"${text}"`;
        card.classList.remove('d-none');
    }
};

window.analyzeNewsWithAI = function() {
    const textEl = document.getElementById('selectedNewsText');
    const symbolSelect = document.getElementById('symbolSelect');
    if (textEl && symbolSelect) {
        const headline = textEl.innerText.replace(/"/g, '');
        const prompt = `Please perform a detailed risk and price impact analysis of the following news headline for ${symbolSelect.value}: "${headline}"`;
        
        // Store prompt to be picked up by chatbot page
        localStorage.setItem('pendingChatPrompt', prompt);
        
        // Redirect to chatbot
        window.location.href = '/chatbot';
    }
};
