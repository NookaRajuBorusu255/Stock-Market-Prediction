/**
 * Advanced AI Chatbot Frontend v2.0
 * Live stock HUD with sparkline, auto-refresh, keyboard shortcuts, message counter
 */

document.addEventListener('DOMContentLoaded', function () {
    const chatContainer    = document.getElementById('chatContainer');
    const chatForm         = document.getElementById('chatForm');
    const userMessageInput = document.getElementById('userMessage');
    const chatSymbolSelect = document.getElementById('chatSymbolSelect');
    const apiModeBadge     = document.getElementById('apiModeBadge');
    const msgCountEl       = document.getElementById('msgCount');

    // HUD elements
    const chatStockHud   = document.getElementById('chatStockHud');
    const hudSymbol      = document.getElementById('hudSymbol');
    const hudPrice       = document.getElementById('hudPrice');
    const hudChange      = document.getElementById('hudChange');
    const hudRsi         = document.getElementById('hudRsi');
    const hudMacd        = document.getElementById('hudMacd');
    const hudSma20       = document.getElementById('hudSma20');
    const hudVol         = document.getElementById('hudVol');
    const hudRsiSignal   = document.getElementById('hudRsiSignal');
    const hudMacdSignal  = document.getElementById('hudMacdSignal');
    const hudActiveModel = document.getElementById('hudActiveModel');
    const hudLastUpdated = document.getElementById('hudLastUpdated');

    let _autoScroll   = true;
    let _liveRefresh  = false;
    let _refreshTimer = null;
    let _msgHistory   = [];          // for ↑ recall
    let _historyIdx   = -1;
    let _msgCount     = 0;

    // ── Populate Symbol Dropdown ──────────────────────────────────
    fetch('/symbols')
        .then(r => r.json())
        .then(symbols => {
            Object.keys(symbols).sort().forEach(sym => {
                const opt = document.createElement('option');
                opt.value   = sym;
                opt.textContent = `${sym} (${symbols[sym].type})`;
                chatSymbolSelect.appendChild(opt);
            });
            const stored = localStorage.getItem('activeStockSymbol');
            if (stored && symbols[stored]) {
                chatSymbolSelect.value = stored;
                updateChatStockHud(stored);
            }
        })
        .catch(err => console.error('Symbol dropdown error:', err));

    // ── Symbol change ─────────────────────────────────────────────
    chatSymbolSelect.addEventListener('change', function () {
        localStorage.setItem('activeStockSymbol', this.value);
        updateChatStockHud(this.value);
    });

    document.getElementById('chatRefreshBtn').addEventListener('click', () => {
        const sym = chatSymbolSelect.value;
        if (sym) updateChatStockHud(sym);
    });

    // ── Live Refresh Toggle (30s auto-poll) ───────────────────────
    const liveRefreshBtn = document.getElementById('liveRefreshToggle');
    liveRefreshBtn.addEventListener('click', function () {
        _liveRefresh = !_liveRefresh;
        if (_liveRefresh) {
            this.style.background = 'rgba(16,185,129,0.18)';
            this.style.borderColor = 'rgba(16,185,129,0.5)';
            this.innerHTML = '<i class="bi bi-reception-4 me-1"></i>Live ON';
            const sym = chatSymbolSelect.value;
            if (sym) updateChatStockHud(sym);
            _refreshTimer = setInterval(() => {
                const s = chatSymbolSelect.value;
                if (s) updateChatStockHud(s);
            }, 30000);
        } else {
            this.style.background = 'rgba(16,185,129,0.07)';
            this.style.borderColor = 'rgba(16,185,129,0.2)';
            this.innerHTML = '<i class="bi bi-reception-4 me-1"></i>Live';
            clearInterval(_refreshTimer);
        }
    });

    // ── Live Stock HUD with Sparkline ─────────────────────────────
    function updateChatStockHud(symbol) {
        if (!symbol) {
            chatStockHud.classList.add('d-none');
            return;
        }

        fetch(`/api/stock/${symbol}/summary`)
            .then(r => r.json())
            .then(data => {
                if (!data || data.error) { chatStockHud.classList.add('d-none'); return; }
                chatStockHud.classList.remove('d-none');

                const isUp = data.change >= 0;
                hudSymbol.textContent = data.symbol;
                hudPrice.innerHTML  = `<span style="color:${isUp ? '#34d399' : '#f87171'}">$${data.price.toFixed(2)}</span>`;
                hudChange.innerHTML = `<span style="color:${isUp ? '#34d399' : '#f87171'};font-size:0.72rem;">
                    ${isUp ? '▲' : '▼'} ${Math.abs(data.change).toFixed(2)} (${isUp ? '+' : ''}${data.pct_change.toFixed(2)}%)
                </span>`;

                // RSI
                if (data.rsi != null && !isNaN(data.rsi)) {
                    hudRsi.textContent = data.rsi.toFixed(1);
                    hudRsi.style.color = data.rsi < 30 ? '#34d399' : data.rsi > 70 ? '#f87171' : '#f8fafc';
                    hudRsiSignal.textContent = data.rsi < 30 ? 'RSI Oversold' : data.rsi > 70 ? 'RSI Overbought' : 'RSI Neutral';
                    hudRsiSignal.className = 'metric-badge ' + (data.rsi < 30 ? 'badge-bullish' : data.rsi > 70 ? 'badge-bearish' : 'badge-neutral');
                }

                // MACD
                if (data.macd != null && data.macd_sig != null) {
                    const bull = data.macd > data.macd_sig;
                    hudMacd.textContent = bull ? '▲ Bullish Cross' : '▼ Bearish Cross';
                    hudMacd.style.color = bull ? '#34d399' : '#f87171';
                    hudMacdSignal.textContent = bull ? 'MACD Bullish' : 'MACD Bearish';
                    hudMacdSignal.className = 'metric-badge ' + (bull ? 'badge-bullish' : 'badge-bearish');
                }

                // SMA20
                if (data.sma20 != null) hudSma20.textContent = `$${data.sma20.toFixed(2)}`;

                // Volatility
                if (data.volatility != null) hudVol.textContent = `${(data.volatility * 100).toFixed(1)}%`;

                // Active model badge
                const activeModel = localStorage.getItem('activePredictModel') || 'XGBoost';
                if (hudActiveModel) {
                    hudActiveModel.textContent = activeModel;
                    hudActiveModel.className = 'metric-badge ' + (activeModel === 'LSTM' ? 'badge-bullish' : 'badge-neutral');
                }

                if (hudLastUpdated) hudLastUpdated.textContent = `Data as of ${data.last_date}`;

                // Draw sparkline from recent close data
                drawSparkline(symbol);
            })
            .catch(() => chatStockHud.classList.add('d-none'));
    }

    // ── Canvas Sparkline (last 30 close prices) ───────────────────
    function drawSparkline(symbol) {
        const canvas = document.getElementById('sparklineCanvas');
        if (!canvas) return;
        const ctx = canvas.getContext('2d');
        canvas.width  = canvas.offsetWidth || 220;
        canvas.height = 40;

        fetch(`/api/stock/${symbol}`)
            .then(r => r.json())
            .then(data => {
                if (!data.close || data.close.length < 5) return;
                const prices = data.close.slice(-30);
                const W = canvas.width, H = canvas.height;
                const min = Math.min(...prices), max = Math.max(...prices);
                const range = max - min || 1;
                const isUp = prices[prices.length - 1] >= prices[0];

                ctx.clearRect(0, 0, W, H);

                // Gradient fill
                const grad = ctx.createLinearGradient(0, 0, 0, H);
                const col = isUp ? '#34d399' : '#f87171';
                grad.addColorStop(0, col + '44');
                grad.addColorStop(1, col + '00');

                ctx.beginPath();
                prices.forEach((p, i) => {
                    const x = (i / (prices.length - 1)) * W;
                    const y = H - ((p - min) / range) * (H - 4) - 2;
                    i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
                });
                // Close fill path
                ctx.lineTo(W, H); ctx.lineTo(0, H); ctx.closePath();
                ctx.fillStyle = grad;
                ctx.fill();

                // Line
                ctx.beginPath();
                prices.forEach((p, i) => {
                    const x = (i / (prices.length - 1)) * W;
                    const y = H - ((p - min) / range) * (H - 4) - 2;
                    i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
                });
                ctx.strokeStyle = col;
                ctx.lineWidth = 1.5;
                ctx.stroke();
            })
            .catch(() => {});
    }

    // ── Load Chat History ─────────────────────────────────────────
    fetch('/api/chatbot/history')
        .then(r => r.json())
        .then(data => {
            if (data.success && data.history.length > 0) {
                chatContainer.innerHTML = '';
                data.history.forEach(msg => appendMessage(msg.message, msg.sender));
                scrollChatToBottom();
                _msgCount = data.history.length;
                updateMsgCount();
            }
        })
        .catch(err => console.error('Chat history error:', err));

    // ── Clear Chat ────────────────────────────────────────────────
    const clearConfirmModalEl = document.getElementById('clearChatConfirmModal');
    document.getElementById('clearChatBtn').addEventListener('click', () => {
        if (clearConfirmModalEl) new bootstrap.Modal(clearConfirmModalEl).show();
        else executeClearChat();
    });

    const confirmClearBtn = document.getElementById('confirmClearChatBtn');
    if (confirmClearBtn) {
        confirmClearBtn.addEventListener('click', () => {
            bootstrap.Modal.getInstance(clearConfirmModalEl)?.hide();
            executeClearChat();
        });
    }

    function executeClearChat() {
        fetch('/api/chatbot/clear', { method: 'POST' })
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    chatContainer.innerHTML = '';
                    _msgCount = 0;
                    updateMsgCount();
                    appendMessage(
                        "Chat cleared. I'm your **EquityAI Stock Assistant**.\n\nTry: **\"Analyze AAPL\"** · **\"Predict TSLA\"** · **\"Compare models\"**",
                        'bot'
                    );
                    scrollChatToBottom();
                    if (typeof showToast === 'function') showToast('Chat history cleared.', 'info');
                }
            })
            .catch(err => console.error('Clear error:', err));
    }

    // ── Quick Pill Buttons ────────────────────────────────────────
    document.querySelectorAll('.quick-pill-btn').forEach(btn => {
        btn.addEventListener('click', function () {
            const action = this.getAttribute('data-action');
            const symbol = chatSymbolSelect.value;
            const queries = {
                analyze:  symbol ? `Analyze ${symbol} price and technical indicators` : 'Analyze the current stock',
                predict:  symbol ? `Predict ${symbol} next close price` : "Predict tomorrow's price",
                sentiment: symbol ? `Show ${symbol} news and sentiment analysis` : 'Show news sentiment',
                lstm:     'Explain LSTM model and how it works',
                compare:  symbol ? `Compare all trained models for ${symbol}` : 'Compare ML models'
            };
            userMessageInput.value = queries[action] || '';
            userMessageInput.focus();
            chatForm.dispatchEvent(new Event('submit'));
        });
    });

    // ── Keyboard Shortcuts ────────────────────────────────────────
    userMessageInput.addEventListener('keydown', function (e) {
        if (e.key === 'ArrowUp' && !e.shiftKey) {
            e.preventDefault();
            if (_historyIdx < _msgHistory.length - 1) {
                _historyIdx++;
                this.value = _msgHistory[_msgHistory.length - 1 - _historyIdx];
            }
        } else if (e.key === 'ArrowDown' && !e.shiftKey) {
            e.preventDefault();
            if (_historyIdx > 0) {
                _historyIdx--;
                this.value = _msgHistory[_msgHistory.length - 1 - _historyIdx];
            } else {
                _historyIdx = -1;
                this.value = '';
            }
        } else if (e.key === 'Escape') {
            this.value = '';
            _historyIdx = -1;
        }
    });

    // ── Form Submit ───────────────────────────────────────────────
    chatForm.addEventListener('submit', function (e) {
        e.preventDefault();
        const message     = userMessageInput.value.trim();
        const activeSymbol = chatSymbolSelect.value;
        if (!message) return;

        _msgHistory.push(message);
        _historyIdx = -1;

        appendMessage(message, 'user');
        userMessageInput.value = '';
        document.getElementById('charCounter').textContent = '0/500';
        _msgCount++;
        updateMsgCount();

        appendTypingIndicator();
        scrollChatToBottom();

        fetch('/api/chatbot/message', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message,
                active_symbol: activeSymbol,
                active_model: localStorage.getItem('activePredictModel') || 'XGBoost'
            })
        })
        .then(r => r.json())
        .then(data => {
            removeTypingIndicator();
            if (data.success) {
                const isGenAI = !data.response.includes('Local Fallback Mode');
                apiModeBadge.innerHTML = isGenAI
                    ? '<i class="bi bi-stars me-1"></i>Gemini AI'
                    : '<i class="bi bi-circle-fill me-1" style="font-size:0.5rem;"></i>Local Mode';
                apiModeBadge.style.background = isGenAI
                    ? 'rgba(99,102,241,0.12)' : 'rgba(16,185,129,0.12)';
                apiModeBadge.style.borderColor = isGenAI
                    ? 'rgba(99,102,241,0.3)' : 'rgba(16,185,129,0.25)';
                apiModeBadge.style.color = isGenAI ? '#a5b4fc' : '#6ee7b7';
                appendMessage(data.response, 'bot', true);
                _msgCount++;
                updateMsgCount();
            } else {
                appendMessage('Error: ' + data.error, 'bot', true);
            }
            scrollChatToBottom();
        })
        .catch(err => {
            removeTypingIndicator();
            appendMessage('Connection error. Check backend logs.', 'bot');
            scrollChatToBottom();
            console.error(err);
        });
    });

    // ── Auto-Scroll ───────────────────────────────────────────────
    chatContainer.addEventListener('scroll', function () {
        const dist = this.scrollHeight - this.scrollTop - this.clientHeight;
        _autoScroll = dist < 60;
        const lockBtn = document.getElementById('scrollLockBtn');
        if (lockBtn) lockBtn.classList.toggle('active', !_autoScroll);
    });

    document.getElementById('scrollLockBtn').addEventListener('click', function () {
        _autoScroll = !_autoScroll;
        this.classList.toggle('active', !_autoScroll);
        if (_autoScroll) scrollChatToBottom();
    });

    function scrollChatToBottom() {
        if (_autoScroll) chatContainer.scrollTop = chatContainer.scrollHeight;
    }

    function updateMsgCount() {
        if (msgCountEl) msgCountEl.textContent = `${_msgCount} message${_msgCount !== 1 ? 's' : ''}`;
    }

    // ── Typing Indicator ──────────────────────────────────────────
    function appendTypingIndicator() {
        const wrap = document.createElement('div');
        wrap.className = 'd-flex align-items-end gap-2 mb-3';
        wrap.id = 'typingIndicator';
        const avatar = document.createElement('div');
        avatar.className = 'chat-avatar chat-avatar-bot';
        avatar.style.cssText = 'width:28px;height:28px;font-size:0.65rem;flex-shrink:0;';
        avatar.textContent = 'AI';
        const bubble = document.createElement('div');
        bubble.className = 'message-bubble message-bot';
        bubble.innerHTML = '<span class="typing-dots"><span></span><span></span><span></span></span>';
        wrap.appendChild(avatar);
        wrap.appendChild(bubble);
        chatContainer.appendChild(wrap);
    }

    function removeTypingIndicator() {
        const el = document.getElementById('typingIndicator');
        if (el) el.remove();
    }

    // ── Append Message ────────────────────────────────────────────
    function appendMessage(text, sender, shouldType = false) {
        const wrap = document.createElement('div');
        wrap.className = `d-flex align-items-end gap-2 mb-3${sender === 'user' ? ' flex-row-reverse' : ''}`;

        const avatar = document.createElement('div');
        avatar.className = `chat-avatar chat-avatar-${sender}`;
        avatar.style.cssText = 'width:28px;height:28px;font-size:0.65rem;flex-shrink:0;';
        avatar.textContent = sender === 'bot' ? 'AI' : 'U';

        const bubble = document.createElement('div');
        bubble.className = `message-bubble message-${sender}`;

        wrap.appendChild(avatar);
        wrap.appendChild(bubble);
        chatContainer.appendChild(wrap);

        if (sender === 'bot') {
            const html = parseMarkdownToHtml(text);
            if (shouldType) {
                const sendBtn = document.getElementById('sendBtn');
                if (sendBtn) sendBtn.disabled = true;
                userMessageInput.disabled = true;
                typeHtmlContent(bubble, html, () => {
                    if (sendBtn) sendBtn.disabled = false;
                    userMessageInput.disabled = false;
                    userMessageInput.focus();
                });
            } else {
                bubble.innerHTML = html;
                scrollChatToBottom();
            }
        } else {
            bubble.textContent = text;
            scrollChatToBottom();
        }
    }

    // ── Typewriter ────────────────────────────────────────────────
    function typeHtmlContent(element, htmlContent, onComplete) {
        const tokens = (htmlContent.match(/(<[^>]+>|[^<>\s]+|\s+)/g) || []);
        let idx = 0;
        const cursor = document.createElement('span');
        cursor.className = 'typing-cursor';
        element.appendChild(cursor);

        function next() {
            if (idx < tokens.length) {
                const token = tokens[idx++];
                cursor.remove();
                element.insertAdjacentHTML('beforeend', token);
                element.appendChild(cursor);
                scrollChatToBottom();
                const delay = token.startsWith('<') ? 0 : token.trim() === '' ? 4 : Math.min(22, 3 + token.length * 2);
                setTimeout(next, delay);
            } else {
                cursor.remove();
                if (onComplete) onComplete();
            }
        }
        next();
    }

    // ── Markdown Parser ───────────────────────────────────────────
    function parseMarkdownToHtml(md) {
        let html = md.replace(/</g, '&lt;').replace(/>/g, '&gt;');

        // Tables
        const lines = html.split('\n');
        let inTable = false, header = [], rows = [], out = [];
        for (let i = 0; i < lines.length; i++) {
            const line = lines[i].trim();
            if (line.startsWith('|') && line.endsWith('|')) {
                if (!inTable) { inTable = true; header = line.split('|').map(s => s.trim()).filter(Boolean); }
                else if (line.includes('---')) continue;
                else rows.push(line.split('|').map(s => s.trim()).filter((_, j, a) => j > 0 && j < a.length - 1));
            } else {
                if (inTable) { out.push(buildTable(header, rows)); inTable = false; header = []; rows = []; }
                out.push(lines[i]);
            }
        }
        if (inTable) out.push(buildTable(header, rows));
        html = out.join('\n');

        html = html.replace(/^### (.*?)$/gm, '<h5 class="text-white mt-3 mb-2" style="font-family:\'Outfit\',sans-serif;">$1</h5>');
        html = html.replace(/^## (.*?)$/gm,  '<h4 class="text-white mt-3 mb-2" style="font-family:\'Outfit\',sans-serif;">$1</h4>');
        html = html.replace(/^# (.*?)$/gm,   '<h3 class="text-white mt-3 mb-2" style="font-family:\'Outfit\',sans-serif;">$1</h3>');
        html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        html = html.replace(/```([\s\S]*?)```/g, '<pre class="chat-code-block"><code>$1</code></pre>');
        html = html.replace(/`(.*?)`/g, '<code class="chat-inline-code">$1</code>');
        html = html.replace(/^\s*[-*]\s+(.*?)$/gm, '<li class="text-secondary mb-1">$1</li>');
        html = html.replace(/(<li[\s\S]*?<\/li>)+/g, '<ul class="ps-3 my-2">$&</ul>');
        html = html.replace(/\n\n/g, '<br><br>');
        return html;

        function buildTable(hs, rs) {
            let t = `<div class="chat-table-wrapper"><table class="chat-table"><thead><tr>`;
            hs.forEach(h => { t += `<th>${h.replace(/\*\*(.*?)\*\*/g, '$1')}</th>`; });
            t += '</tr></thead><tbody>';
            rs.forEach(r => {
                t += '<tr>';
                r.forEach(cell => {
                    let c = cell.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
                    if (c.includes('▲ Bullish') || c.includes('Bullish'))
                        c = `<span class="metric-badge badge-bullish" style="font-size:0.72rem;"><i class="bi bi-graph-up-arrow me-1"></i>Bullish</span>`;
                    else if (c.includes('▼ Bearish') || c.includes('Bearish'))
                        c = `<span class="metric-badge badge-bearish" style="font-size:0.72rem;"><i class="bi bi-graph-down-arrow me-1"></i>Bearish</span>`;
                    const m = c.match(/(\d+(?:\.\d+)?)%/);
                    if (m) {
                        const v = parseFloat(m[1]);
                        c = `<div class="d-flex align-items-center gap-2"><span>${v.toFixed(1)}%</span>
                            <div class="chat-progress-container" style="width:48px;"><div class="chat-progress-bar" style="width:${v}%;"></div></div></div>`;
                    }
                    t += `<td>${c}</td>`;
                });
                t += '</tr>';
            });
            t += '</tbody></table></div>';
            return t;
        }
    }

    // ── Pending prompt from dashboard ─────────────────────────────
    const pending = localStorage.getItem('pendingChatPrompt');
    if (pending) {
        localStorage.removeItem('pendingChatPrompt');
        userMessageInput.value = pending;
        chatForm.dispatchEvent(new Event('submit'));
    }
});
