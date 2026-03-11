(function () {
    function createCallcheckController(config, domRefs) {
        const state = {
            stopped: false,
            realtimeStarted: false,
            pollingStarted: false,
            fallbackActivated: false,
            backoffIndex: 0,
            consecutiveErrors: 0,
            sse: null,
            timers: {
                poll: null,
                sseSilence: null,
            },
            callPhone: config.callPhone || null,
            lastQrPhone: null,
        };

        function isMobileDevice() {
            return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent)
                || (window.matchMedia && window.matchMedia('(max-width: 768px)').matches);
        }

        function clearTimer(name) {
            if (!state.timers[name]) {
                return;
            }
            clearTimeout(state.timers[name]);
            state.timers[name] = null;
        }

        function clearAllTimers() {
            clearTimer('poll');
            clearTimer('sseSilence');
        }

        function closeSSE() {
            if (!state.sse) {
                return;
            }
            state.sse.onmessage = null;
            state.sse.onerror = null;
            state.sse.close();
            state.sse = null;
        }

        function stopChecks() {
            state.stopped = true;
            clearAllTimers();
            closeSSE();
        }

        function hideFallbackButton() {
            if (!domRefs.callActionButton) {
                return;
            }
            domRefs.callActionButton.style.display = 'none';
        }

        function showFallbackButton() {
            if (!config.manualFallbackEnabled || !domRefs.callActionButton) {
                return;
            }
            domRefs.callActionButton.style.display = '';
        }

        function setError(message) {
            if (!domRefs.errorNotify) {
                return;
            }
            domRefs.errorNotify.textContent = message;
            domRefs.errorNotify.style.display = 'block';
        }

        function clearError() {
            if (!domRefs.errorNotify) {
                return;
            }
            domRefs.errorNotify.textContent = '';
            domRefs.errorNotify.style.display = 'none';
        }

        function generateQR(content, text) {
            if (!domRefs.qrCanvas) {
                return;
            }

            const qrSize = 240;
            const padding = 30;
            const footerHeight = 50;
            const radius = 15;
            const borderColor = '#000';
            const white = '#ffffff';

            const canvas = domRefs.qrCanvas;
            const ctx = canvas.getContext('2d');

            canvas.width = qrSize + padding * 2;
            canvas.height = qrSize + padding * 2 + footerHeight;

            const width = canvas.width;
            const height = canvas.height;

            ctx.clearRect(0, 0, width, height);

            ctx.beginPath();
            ctx.roundRect(0, 0, width, height, radius);
            ctx.fillStyle = borderColor;
            ctx.fill();

            ctx.beginPath();

            const qrZoneHeight = qrSize + padding * 2;
            const qrPadding = Math.round(padding / 2);

            ctx.moveTo(qrPadding, qrPadding + radius);
            ctx.arcTo(qrPadding, qrPadding, qrPadding + radius, qrPadding, radius);
            ctx.lineTo(width - radius - qrPadding, qrPadding);
            ctx.arcTo(width - qrPadding, qrPadding, width - qrPadding, qrPadding + radius, radius);
            ctx.lineTo(width - qrPadding, qrZoneHeight - radius - qrPadding);
            ctx.arcTo(width - qrPadding, qrZoneHeight - qrPadding, width - qrPadding - radius, qrZoneHeight - qrPadding, radius);
            ctx.lineTo(radius + qrPadding, qrZoneHeight - qrPadding);
            ctx.arcTo(qrPadding, qrZoneHeight - qrPadding, qrPadding, qrZoneHeight - qrPadding - radius, radius);

            ctx.closePath();

            ctx.fillStyle = '#fff';
            ctx.fill();

            const qrCanvas = document.createElement('canvas');
            QRCode.toCanvas(qrCanvas, content, {
                width: qrSize,
                margin: 0,
                errorCorrectionLevel: 'H',
            }, function (error) {
                if (error) {
                    console.error(error);
                    return;
                }

                ctx.drawImage(qrCanvas, padding, padding);

                ctx.fillStyle = white;
                ctx.font = 'bold 26px Arial';
                ctx.textAlign = 'center';
                ctx.textBaseline = 'middle';
                ctx.fillText(text, width / 2, qrZoneHeight + footerHeight / 2);
            });
        }

        function updateCallLink(number) {
            if (!number || !domRefs.callLinkButton) {
                return;
            }

            const nextPhone = String(number);
            const phoneChanged = state.callPhone !== nextPhone;
            state.callPhone = nextPhone;

            domRefs.callLinkButton.href = 'tel:' + nextPhone;
            domRefs.callLinkButton.textContent = nextPhone;
            domRefs.callLinkButton.style.display = '';
            hideFallbackButton();

            const shouldShowQr = !isMobileDevice() && domRefs.qrCanvas;
            if (!shouldShowQr) {
                if (domRefs.qrCanvas) {
                    domRefs.qrCanvas.style.display = 'none';
                }
                return;
            }

            if (phoneChanged || state.lastQrPhone !== nextPhone) {
                generateQR('tel:' + nextPhone, nextPhone);
                state.lastQrPhone = nextPhone;
            }

            domRefs.qrCanvas.style.display = '';
        }

        function switchToManualFallback(message) {
            if (state.fallbackActivated || config.iphoneMode || !config.manualFallbackEnabled) {
                return;
            }
            state.fallbackActivated = true;
            state.pollingStarted = false;
            state.realtimeStarted = false;
            stopChecks();
            showFallbackButton();
            if (message) {
                setError(message);
            }
        }

        function applyState(payload) {
            if (state.stopped || !payload || !payload.state) {
                return;
            }

            if (payload.state === 'verified') {
                stopChecks();
                window.location.href = config.callAuthUrl;
                return;
            }

            if (payload.state === 'pending') {
                state.consecutiveErrors = 0;
                return;
            }

            if (payload.state === 'failed') {
                setError(payload.message || config.defaultFailedMessage);
                stopChecks();
                return;
            }

            if (payload.state === 'timeout') {
                setError(payload.message || config.defaultTimeoutMessage);
                stopChecks();
                return;
            }

            setError(config.defaultFailedMessage);
            stopChecks();
        }

        async function fetchJson(url, options, fallbackErrorMessage) {
            const response = await fetch(url, options);
            const body = await response.text();

            let payload = {};
            if (body) {
                try {
                    payload = JSON.parse(body);
                } catch (error) {
                    throw new Error(fallbackErrorMessage);
                }
            }

            if (!response.ok) {
                throw new Error((payload && payload.message) || fallbackErrorMessage || ('HTTP ' + response.status));
            }

            return payload;
        }

        async function fetchCallState() {
            return fetchJson(
                config.callCheckUrl,
                {
                    method: 'GET',
                    headers: {
                        'Accept': 'application/json',
                    },
                },
                config.defaultPollingErrorMessage
            );
        }

        function scheduleSseSilenceCheck() {
            if (state.stopped || !state.sse) {
                return;
            }
            clearTimer('sseSilence');
            state.timers.sseSilence = setTimeout(function () {
                verifyOnceBeforeFallback();
            }, config.sseSilenceTimeoutMs);
        }

        function scheduleNextPoll() {
            if (state.stopped) {
                return;
            }
            const delay = config.pollBackoffMs[Math.min(state.backoffIndex, config.pollBackoffMs.length - 1)];
            state.backoffIndex += 1;
            clearTimer('poll');
            state.timers.poll = setTimeout(function () {
                poll();
            }, delay);
        }

        async function verifyOnceBeforeFallback() {
            if (state.stopped || !state.sse) {
                return;
            }

            try {
                const payload = await fetchCallState();
                applyState(payload);
                if (!state.stopped && payload.state === 'pending' && state.sse) {
                    scheduleSseSilenceCheck();
                }
            } catch (error) {
                console.warn('SSE silence check failed:', error);
                switchToManualFallback(config.manualFallbackMessage);
            }
        }

        async function poll() {
            if (state.stopped) {
                return;
            }

            try {
                const payload = await fetchCallState();
                applyState(payload);
                if (!state.stopped && payload.state === 'pending') {
                    scheduleNextPoll();
                }
                return;
            } catch (error) {
                console.error('Polling error:', error);
                state.consecutiveErrors += 1;
                if (state.consecutiveErrors >= config.maxConsecutiveErrors) {
                    switchToManualFallback(config.defaultPollingErrorMessage);
                    return;
                }
            }

            scheduleNextPoll();
        }

        function startPolling() {
            if (state.stopped || state.pollingStarted) {
                return;
            }
            closeSSE();
            clearTimer('sseSilence');
            state.pollingStarted = true;
            state.backoffIndex = 0;
            state.consecutiveErrors = 0;
            poll();
        }

        function startSSE() {
            if (state.stopped) {
                return;
            }

            if (typeof EventSource === 'undefined') {
                switchToManualFallback(config.manualFallbackMessage);
                return;
            }

            state.sse = new EventSource(config.callCheckSseUrl);
            scheduleSseSilenceCheck();

            state.sse.onmessage = function (event) {
                if (state.stopped) {
                    return;
                }

                try {
                    const payload = JSON.parse(event.data);
                    scheduleSseSilenceCheck();
                    applyState(payload);
                } catch (error) {
                    console.error('Invalid SSE payload:', error);
                    switchToManualFallback(config.manualFallbackMessage);
                }
            };

            state.sse.onerror = function (event) {
                if (state.stopped) {
                    return;
                }
                console.warn('SSE error:', event);
                switchToManualFallback(config.manualFallbackMessage);
            };
        }

        function startRealtimeChecks() {
            if (state.realtimeStarted) {
                return;
            }

            state.stopped = false;
            state.realtimeStarted = true;
            state.pollingStarted = false;
            state.fallbackActivated = false;
            closeSSE();
            clearAllTimers();

            startSSE();
            if (!config.iphoneMode && !state.sse) {
                startPolling();
            }
        }

        function delay(ms) {
            return new Promise(function (resolve) {
                setTimeout(resolve, ms);
            });
        }

        function spawnHiddenIframe(src) {
            const iframe = document.createElement('iframe');
            iframe.style.display = 'none';
            iframe.src = src;
            document.body.appendChild(iframe);
            setTimeout(function () {
                iframe.remove();
            }, 5000);
        }

        async function startManualFlow() {
            if (!domRefs.callActionButton) {
                return;
            }

            domRefs.callActionButton.disabled = true;
            domRefs.callActionButton.textContent = config.preparingPhoneMessage;
            clearError();

            try {
                const payload = await fetchJson(
                    config.callStartUrl,
                    {
                        method: 'POST',
                        headers: {
                            'Accept': 'application/json',
                        },
                    },
                    config.defaultFailedMessage
                );

                if (payload.state === 'sending_code') {
                    window.location.href = payload.redirect_url || config.codeSendUrl;
                    return;
                }

                if (!payload.call_phone) {
                    throw new Error(config.defaultFailedMessage);
                }

                spawnHiddenIframe(config.trialSendinUrl);

                if (config.iphoneMode) {
                    await delay(3000);
                    spawnHiddenIframe(config.captiveAppleUrl);
                }

                updateCallLink(payload.call_phone);
                startRealtimeChecks();
            } catch (error) {
                setError(error.message || config.defaultFailedMessage);
            } finally {
                domRefs.callActionButton.disabled = false;
                domRefs.callActionButton.textContent = config.getPhoneButtonMessage;
            }
        }

        function init() {
            if (domRefs.callActionButton) {
                domRefs.callActionButton.addEventListener('click', startManualFlow);
            }

            if (state.callPhone) {
                updateCallLink(state.callPhone);
            } else if (domRefs.qrCanvas) {
                domRefs.qrCanvas.style.display = 'none';
            }

            if (config.iphoneMode) {
                showFallbackButton();
                return;
            }

            startRealtimeChecks();
        }

        return {
            init: init,
            startRealtimeChecks: startRealtimeChecks,
            startManualFlow: startManualFlow,
            updateCallLink: updateCallLink,
        };
    }

    window.createCallcheckController = createCallcheckController;
})();
