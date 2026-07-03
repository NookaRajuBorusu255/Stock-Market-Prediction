/**
 * AI Chatbot Frontend Interface Handler
 * Binds chat submissions, prints typing indicators, and parses Markdown responses
 */

document.addEventListener('DOMContentLoaded', function() {
    const chatContainer = document.getElementById('chatContainer');
    const chatForm = document.getElementById('chatForm');
    const userMessageInput = document.getElementById('userMessage');
    const chatSymbolSelect = document.getElementById('chatSymbolSelect');
    const apiModeBadge = document.getElementById('apiModeBadge');
    
    // Stock Status HUD elements
    const chatStockHud = document.getElementById('chatStockHud');
    const hudSymbol = document.getElementById('hudSymbol');
    const hudPrice = document.getElementById('hudPrice');
    const hudRsi = document.getElementById('hudRsi');
    const hudMacd = document.getElementById('hudMacd');
    
    // 1. Populate Stock Symbols Context select
    fetch('/symbols')
    .then(response => response.json())
    .then(symbols => {
        // symbols is { 'AAPL': { 'path': ..., 'type': ... } }
        Object.keys(symbols).forEach(symbol => {
            const opt = document.createElement('option');
            opt.value = symbol;
            opt.innerText = `${symbol} (${symbols[symbol].type})`;
            chatSymbolSelect.appendChild(opt);
        });
        
        // Load default focus if saved in localStorage (shared key)
        const storedSymbol = localStorage.getItem('activeStockSymbol');
        if (storedSymbol && symbols[storedSymbol]) {
            chatSymbolSelect.value = storedSymbol;
            updateChatStockHud(storedSymbol);
        }
    })
    .catch(err => console.error("Error populating chat symbol context:", err));

    // Save symbol changes to localStorage (shared key) and update HUD
    chatSymbolSelect.addEventListener('change', function(e) {
        localStorage.setItem('activeStockSymbol', e.target.value);
        updateChatStockHud(e.target.value);
    });

    function updateChatStockHud(symbol) {
        if (!symbol) {
            chatStockHud.classList.add('d-none');
            return;
        }
        
        fetch(`/api/stock/${symbol}`)
        .then(res => res.json())
        .then(data => {
            if (data && data.price) {
                chatStockHud.classList.remove('d-none');
                hudSymbol.innerText = data.symbol;
                
                const changeSign = data.change >= 0 ? '+' : '';
                const colorClass = data.change >= 0 ? 'text-success' : 'text-danger';
                hudPrice.innerHTML = `<span class="${colorClass}">$${data.price.toFixed(2)} (${changeSign}${data.pct_change.toFixed(2)}%)</span>`;
                
                // RSI Status
                if (data.rsi && !isNaN(data.rsi)) {
                    hudRsi.innerText = data.rsi.toFixed(2);
                    if (data.rsi < 30) {
                        hudRsi.className = 'metric-badge py-0.5 px-2 badge-bullish';
                    } else if (data.rsi > 70) {
                        hudRsi.className = 'metric-badge py-0.5 px-2 badge-bearish';
                    } else {
                        hudRsi.className = 'metric-badge py-0.5 px-2 badge-neutral';
                    }
                } else {
                    hudRsi.innerText = 'N/A';
                    hudRsi.className = 'metric-badge py-0.5 px-2 badge-neutral';
                }
                
                // MACD crossover
                if (data.macd && data.macd_sig && !isNaN(data.macd) && !isNaN(data.macd_sig)) {
                    const isBull = data.macd > data.macd_sig;
                    hudMacd.innerText = isBull ? 'Bullish Crossover' : 'Bearish Crossunder';
                    hudMacd.className = isBull ? 'metric-badge py-0.5 px-2 badge-bullish' : 'metric-badge py-0.5 px-2 badge-bearish';
                } else {
                    hudMacd.innerText = 'N/A';
                    hudMacd.className = 'metric-badge py-0.5 px-2 badge-neutral';
                }
                
                // Active Model Status
                const activeModel = localStorage.getItem('activePredictModel') || 'XGBoost';
                const hudActiveModel = document.getElementById('hudActiveModel');
                if (hudActiveModel) {
                    hudActiveModel.innerText = activeModel;
                    if (activeModel === 'LSTM') {
                        hudActiveModel.className = 'metric-badge py-0.5 px-2 badge-bullish';
                    } else {
                        hudActiveModel.className = 'metric-badge py-0.5 px-2 badge-neutral';
                    }
                }
            } else {
                chatStockHud.classList.add('d-none');
            }
        })
        .catch(err => {
            console.error("Error loading chat stock HUD:", err);
            chatStockHud.classList.add('d-none');
        });
    }

    // Load existing SQL chat history logs
    fetch('/api/chatbot/history')
    .then(response => response.json())
    .then(data => {
        if (data.success && data.history.length > 0) {
            // Remove initial welcome bubble
            chatContainer.innerHTML = '';
            data.history.forEach(msg => {
                appendMessage(msg.message, msg.sender);
            });
            scrollChatToBottom();
        }
    })
    .catch(err => console.error("Error loading chat history:", err));

    // Clear history handler
    const clearChatBtn = document.getElementById('clearChatBtn');
    clearChatBtn.addEventListener('click', function() {
        if (!confirm("Are you sure you want to delete all chat history?")) return;
        
        fetch('/api/chatbot/clear', { method: 'POST' })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Clear UI container
                chatContainer.innerHTML = `
                    <div class="d-flex mb-3">
                        <div class="message-bubble message-bot">
                            Hello! I am your AI-Powered Stock Assistant. I can describe machine learning algorithms (LSTM, Random Forest, XGBoost), technical indicators (RSI, MACD, SMAs), and analyze local stock datasets.
                            <br><br>
                            Try asking: **"What is LSTM?"** or **"Analyze AAPL price"**.
                        </div>
                    </div>
                `;
                scrollChatToBottom();
            } else {
                alert("Failed to clear chat log: " + data.error);
            }
        })
        .catch(err => console.error("Clear chat network error:", err));
    });

    // Quick Action suggestion pills handler
    document.querySelectorAll('.quick-pill-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const action = this.getAttribute('data-action');
            const symbol = chatSymbolSelect.value;
            
            let query = "";
            if (action === 'analyze') {
                query = symbol ? `Analyze ${symbol} price` : "Analyze stock summary";
            } else if (action === 'predict') {
                query = symbol ? `Predict ${symbol} price` : "Predict tomorrow's price";
            } else if (action === 'sentiment') {
                query = symbol ? `Show ${symbol} news and sentiment` : "Show news sentiment";
            } else if (action === 'lstm') {
                query = "Explain LSTM model";
            }
            
            userMessageInput.value = query;
            // Submit form
            chatForm.dispatchEvent(new Event('submit'));
        });
    });

    // 2. Form submission handler
    chatForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        const message = userMessageInput.value.trim();
        const activeSymbol = chatSymbolSelect.value;
        
        if (!message) return;
        
        // Append user bubble
        appendMessage(message, 'user');
        
        // Clear input
        userMessageInput.value = '';
        
        // Display thinking loader
        appendTypingIndicator();
        scrollChatToBottom();
        
        // Call backend API
        fetch('/api/chatbot/message', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message: message,
                active_symbol: activeSymbol,
                active_model: localStorage.getItem('activePredictModel') || 'XGBoost'
            })
        })
        .then(response => response.json())
        .then(data => {
            removeTypingIndicator();
            
            if (data.success) {
                // Update badge if backend indicates it used generative LLM or fallback
                if (data.response.includes('Local Fallback Mode')) {
                    apiModeBadge.innerText = 'Local Mode';
                    apiModeBadge.className = 'badge bg-success-subtle text-success border border-success-subtle rounded-pill px-3 py-2 small';
                } else {
                    apiModeBadge.innerText = 'Generative AI';
                    apiModeBadge.className = 'badge bg-primary-subtle text-primary border border-primary-subtle rounded-pill px-3 py-2 small';
                }
                
                appendMessage(data.response, 'bot', true);
            } else {
                appendMessage("Failed to process request: " + data.error, 'bot', true);
            }
            scrollChatToBottom();
        })
        .catch(err => {
            removeTypingIndicator();
            appendMessage("Connection error occurred. Check backend logs.", 'bot');
            scrollChatToBottom();
            console.error(err);
        });
    });

    // Helper to print HTML tags whole and text elements word-by-word
    function typeHtmlContent(element, htmlContent, onComplete) {
        const regex = /(<[^>]+>|[^<>\s]+|\s+)/g;
        const tokens = htmlContent.match(regex) || [];
        let currentTokenIdx = 0;
        
        const cursor = document.createElement('span');
        cursor.className = 'typing-cursor';
        element.appendChild(cursor);
        
        function printNextToken() {
            if (currentTokenIdx < tokens.length) {
                const token = tokens[currentTokenIdx];
                currentTokenIdx++;
                
                cursor.remove();
                element.insertAdjacentHTML('beforeend', token);
                element.appendChild(cursor);
                scrollChatToBottom();
                
                let delay = 20; 
                if (token.trim() === '') {
                    delay = 5;
                } else if (token.startsWith('<')) {
                    delay = 0; // render HTML tag structure instantly
                } else {
                    delay = Math.min(20, 3 + token.length * 2);
                }
                
                setTimeout(printNextToken, delay);
            } else {
                cursor.remove();
                if (onComplete) onComplete();
            }
        }
        
        printNextToken();
    }

    function appendMessage(text, sender, shouldType = false) {
        const bubbleWrap = document.createElement('div');
        bubbleWrap.className = `d-flex mb-3`;
        
        const bubble = document.createElement('div');
        bubble.className = `message-bubble message-${sender}`;
        
        bubbleWrap.appendChild(bubble);
        chatContainer.appendChild(bubbleWrap);
        
        if (sender === 'bot') {
            const htmlContent = parseMarkdownToHtml(text);
            if (shouldType) {
                const sendBtn = document.getElementById('sendBtn');
                const userMessageInput = document.getElementById('userMessage');
                if (sendBtn) sendBtn.disabled = true;
                if (userMessageInput) userMessageInput.disabled = true;
                
                typeHtmlContent(bubble, htmlContent, () => {
                    if (sendBtn) sendBtn.disabled = false;
                    if (userMessageInput) {
                        userMessageInput.disabled = false;
                        userMessageInput.focus();
                    }
                });
            } else {
                bubble.innerHTML = htmlContent;
                scrollChatToBottom();
            }
        } else {
            bubble.textContent = text;
            scrollChatToBottom();
        }
    }

    function appendTypingIndicator() {
        const bubbleWrap = document.createElement('div');
        bubbleWrap.className = `d-flex mb-3`;
        bubbleWrap.id = 'typingIndicator';
        
        const bubble = document.createElement('div');
        bubble.className = `message-bubble message-bot`;
        bubble.innerHTML = `<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span> Thinking...`;
        
        bubbleWrap.appendChild(bubble);
        chatContainer.appendChild(bubbleWrap);
    }

    function removeTypingIndicator() {
        const indicator = document.getElementById('typingIndicator');
        if (indicator) {
            indicator.remove();
        }
    }

    function scrollChatToBottom() {
        chatContainer.scrollTop = chatContainer.scrollHeight;
    }

    /**
     * Highly robust local Markdown regex parser
     * Converts bolding, headers, lists, code strings, and newlines to HTML blocks
     */
    function parseMarkdownToHtml(mdText) {
        let html = mdText;
        
        // Escape standard HTML tags to prevent XSS
        html = html.replace(/</g, "&lt;").replace(/>/g, "&gt;");

        // Table parsing
        const lines = html.split('\n');
        let inTable = false;
        let tableHeader = [];
        let tableRows = [];
        let newLines = [];
        
        for (let i = 0; i < lines.length; i++) {
            const line = lines[i].trim();
            if (line.startsWith('|') && line.endsWith('|')) {
                if (!inTable) {
                    inTable = true;
                    tableHeader = line.split('|').map(s => s.trim()).filter(s => s);
                } else if (line.includes('---')) {
                    continue;
                } else {
                    const cols = line.split('|').map(s => s.trim()).filter((s, idx) => idx > 0 && idx < line.split('|').length - 1);
                    tableRows.push(cols);
                }
            } else {
                if (inTable) {
                    newLines.push(buildHtmlTable(tableHeader, tableRows));
                    inTable = false;
                    tableHeader = [];
                    tableRows = [];
                }
                newLines.push(lines[i]);
            }
        }
        if (inTable) {
            newLines.push(buildHtmlTable(tableHeader, tableRows));
        }
        html = newLines.join('\n');
        
        // Headers (### Header)
        html = html.replace(/^### (.*?)$/gm, '<h5 class="text-white mt-3 mb-2 font-outfit">$1</h5>');
        html = html.replace(/^## (.*?)$/gm, '<h4 class="text-white mt-3 mb-2 font-outfit">$1</h4>');
        html = html.replace(/^# (.*?)$/gm, '<h3 class="text-white mt-3 mb-2 font-outfit">$1</h3>');
        
        // Bold (**text**)
        html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        
        // Code Blocks (```code```)
        html = html.replace(/```(.*?)```/gs, '<pre class="bg-black text-info p-3 rounded my-2 small"><code>$1</code></pre>');
        
        // Inline Code (`code`)
        html = html.replace(/`(.*?)`/g, '<code class="bg-dark text-info px-1 py-0.5 rounded small font-monospace">$1</code>');
        
        // Bullet Lists (- item or * item)
        html = html.replace(/^\s*[-*]\s+(.*?)$/gm, '<li class="text-secondary mb-1">$1</li>');
        
        // Wrap contiguous <li> tags in <ul> tags
        html = html.replace(/(<li.*?>.*?<\/li>)+/g, '<ul class="ps-3 my-2">$1</ul>');
        
        // Double newlines into paragraphs, single into linebreaks
        html = html.replace(/\n\n/g, '<br><br>');

        return html;

        function buildHtmlTable(headers, rows) {
            let table = `<div class="chat-table-wrapper"><table class="chat-table"><thead><tr>`;
            headers.forEach(h => {
                const parsedHeader = h.replace(/\*\*(.*?)\*\*/g, '$1');
                table += `<th>${parsedHeader}</th>`;
            });
            table += `</tr></thead><tbody>`;
            rows.forEach(r => {
                table += `<tr>`;
                r.forEach(col => {
                    let cell = col;
                    cell = cell.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
                    cell = cell.replace(/`(.*?)`/g, '<code class="bg-dark text-info px-1 py-0.5 rounded small font-monospace">$1</code>');
                    
                    if (cell.includes('▲ Bullish')) {
                        cell = `<span class="metric-badge badge-bullish py-0.5 px-2 font-weight-bold" style="font-size: 0.75rem;"><i class="bi bi-graph-up-arrow me-1"></i>Bullish</span>`;
                    } else if (cell.includes('▼ Bearish')) {
                        cell = `<span class="metric-badge badge-bearish py-0.5 px-2 font-weight-bold" style="font-size: 0.75rem;"><i class="bi bi-graph-down-arrow me-1"></i>Bearish</span>`;
                    }
                    
                    const confMatch = cell.match(/(\d+(?:\.\d+)?)%/);
                    if (confMatch) {
                        const pctVal = parseFloat(confMatch[1]);
                        cell = `
                            <div class="d-flex align-items-center gap-2">
                                <span>${pctVal.toFixed(1)}%</span>
                                <div class="chat-progress-container" style="width: 50px;">
                                    <div class="chat-progress-bar" style="width: ${pctVal}%;"></div>
                                </div>
                            </div>
                        `;
                    }
                    
                    table += `<td>${cell}</td>`;
                });
                table += `</tr>`;
            });
            table += `</tbody></table></div>`;
            return table;
        }
    }

    // Check if there is a pending headline analysis prompt from dashboard
    const pendingPrompt = localStorage.getItem('pendingChatPrompt');
    if (pendingPrompt) {
        localStorage.removeItem('pendingChatPrompt');
        userMessageInput.value = pendingPrompt;
        chatForm.dispatchEvent(new Event('submit'));
    }
});
