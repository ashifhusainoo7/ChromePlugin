/**
 * Enterprise Google Meet Sentiment Bot - Content Script
 * Injected into Google Meet pages to handle meeting automation and audio capture
 */

class MeetContentScript {
    constructor() {
        this.isActive = false;
        this.audioContext = null;
        this.mediaRecorder = null;
        this.audioChunks = [];
        this.participantObserver = null;
        this.chatObserver = null;
        this.port = null;
        
        this.init();
    }

    async init() {
        try {
            // Wait for page to be fully loaded
            await this.waitForPageLoad();
            
            // Establish connection with background script
            this.setupBackgroundConnection();
            
            // Set up DOM observers
            this.setupObservers();
            
            // Set up audio capture
            await this.setupAudioCapture();
            
            // Auto-configure meeting settings
            this.configureMeetingSettings();
            
            console.log('Meet content script initialized');
            this.sendMessage('MEETING_JOINED', { url: window.location.href });
            
        } catch (error) {
            console.error('Content script initialization failed:', error);
        }
    }

    waitForPageLoad() {
        return new Promise((resolve) => {
            if (document.readyState === 'complete') {
                resolve();
            } else {
                window.addEventListener('load', resolve);
            }
        });
    }

    setupBackgroundConnection() {
        try {
            this.port = chrome.runtime.connect({ name: 'meetingBot' });
            
            this.port.onMessage.addListener((message) => {
                this.handleBackgroundMessage(message);
            });
            
            this.port.onDisconnect.addListener(() => {
                console.log('Background connection lost, attempting reconnect...');
                setTimeout(() => this.setupBackgroundConnection(), 1000);
            });
            
        } catch (error) {
            console.error('Failed to connect to background script:', error);
        }
    }

    handleBackgroundMessage(message) {
        switch (message.type) {
            case 'START_RECORDING':
                this.startAudioRecording();
                break;
                
            case 'STOP_RECORDING':
                this.stopAudioRecording();
                break;
                
            case 'CONFIGURE_MEETING':
                this.configureMeetingSettings(message.config);
                break;
                
            case 'GET_PARTICIPANTS':
                this.sendParticipantInfo();
                break;
                
            case 'MUTE_MICROPHONE':
                this.toggleMicrophone(false);
                break;
                
            case 'UNMUTE_MICROPHONE':
                this.toggleMicrophone(true);
                break;
                
            case 'TOGGLE_VIDEO':
                this.toggleVideo(message.enabled);
                break;
        }
    }

    setupObservers() {
        // Monitor participant changes
        this.setupParticipantObserver();
        
        // Monitor chat messages
        this.setupChatObserver();
        
        // Monitor meeting state changes
        this.setupMeetingStateObserver();
    }

    setupParticipantObserver() {
        const participantSelectors = [
            '[data-participant-id]',
            '[data-self-name]',
            '.participants-list',
            '.participant-grid'
        ];

        const targetNode = document.body;
        this.participantObserver = new MutationObserver((mutations) => {
            let participantChanged = false;
            
            mutations.forEach((mutation) => {
                if (mutation.type === 'childList') {
                    mutation.addedNodes.forEach((node) => {
                        if (node.nodeType === Node.ELEMENT_NODE) {
                            participantSelectors.forEach(selector => {
                                if (node.matches && node.matches(selector) || 
                                    node.querySelector && node.querySelector(selector)) {
                                    participantChanged = true;
                                }
                            });
                        }
                    });
                }
            });
            
            if (participantChanged) {
                setTimeout(() => this.sendParticipantInfo(), 500);
            }
        });

        this.participantObserver.observe(targetNode, {
            childList: true,
            subtree: true
        });
    }

    setupChatObserver() {
        const chatContainer = this.findChatContainer();
        
        if (chatContainer) {
            this.chatObserver = new MutationObserver((mutations) => {
                mutations.forEach((mutation) => {
                    if (mutation.type === 'childList') {
                        mutation.addedNodes.forEach((node) => {
                            if (node.nodeType === Node.ELEMENT_NODE && 
                                this.isChatMessage(node)) {
                                this.processChatMessage(node);
                            }
                        });
                    }
                });
            });

            this.chatObserver.observe(chatContainer, {
                childList: true,
                subtree: true
            });
        }
    }

    setupMeetingStateObserver() {
        // Monitor for meeting end, connection issues, etc.
        const stateSelectors = [
            '[data-call-ended]',
            '.meeting-ended',
            '.connection-error',
            '.rejoining'
        ];

        const observer = new MutationObserver((mutations) => {
            mutations.forEach((mutation) => {
                if (mutation.type === 'childList' || mutation.type === 'attributes') {
                    stateSelectors.forEach(selector => {
                        const element = document.querySelector(selector);
                        if (element) {
                            this.handleMeetingStateChange(selector, element);
                        }
                    });
                }
            });
        });

        observer.observe(document.body, {
            childList: true,
            subtree: true,
            attributes: true,
            attributeFilter: ['data-call-ended', 'class']
        });
    }

    async setupAudioCapture() {
        try {
            // Request microphone permissions
            const stream = await navigator.mediaDevices.getUserMedia({ 
                audio: {
                    echoCancellation: true,
                    noiseSuppression: true,
                    sampleRate: 16000
                } 
            });
            
            this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
            const source = this.audioContext.createMediaStreamSource(stream);
            
            // Set up audio processing
            this.setupAudioProcessing(source);
            
            console.log('Audio capture initialized');
            
        } catch (error) {
            console.error('Failed to setup audio capture:', error);
            this.sendMessage('AUDIO_ERROR', { error: error.message });
        }
    }

    setupAudioProcessing(source) {
        const analyser = this.audioContext.createAnalyser();
        analyser.fftSize = 2048;
        
        const bufferLength = analyser.frequencyBinCount;
        const dataArray = new Uint8Array(bufferLength);
        
        source.connect(analyser);
        
        // Process audio in chunks for real-time analysis
        const processAudio = () => {
            if (!this.isActive) return;
            
            analyser.getByteFrequencyData(dataArray);
            
            // Send audio data for processing
            this.sendAudioData(dataArray);
            
            requestAnimationFrame(processAudio);
        };
        
        // Start processing when recording begins
        this.audioProcessLoop = processAudio;
    }

    startAudioRecording() {
        if (this.isActive) return;
        
        this.isActive = true;
        this.audioChunks = [];
        
        if (this.audioProcessLoop) {
            this.audioProcessLoop();
        }
        
        console.log('Audio recording started');
        this.sendMessage('RECORDING_STARTED', { timestamp: Date.now() });
    }

    stopAudioRecording() {
        this.isActive = false;
        
        if (this.mediaRecorder && this.mediaRecorder.state === 'recording') {
            this.mediaRecorder.stop();
        }
        
        console.log('Audio recording stopped');
        this.sendMessage('RECORDING_STOPPED', { timestamp: Date.now() });
    }

    sendAudioData(audioData) {
        if (!this.isActive) return;
        
        // Convert to base64 for transmission
        const audioBuffer = Array.from(audioData);
        
        this.sendMessage('AUDIO_DATA', {
            data: audioBuffer,
            timestamp: Date.now(),
            sampleRate: this.audioContext.sampleRate
        });
    }

    configureMeetingSettings(config = {}) {
        // Auto-mute microphone if configured
        if (config.muteOnJoin !== false) {
            this.toggleMicrophone(false);
        }
        
        // Auto-disable video if configured
        if (config.disableVideo !== false) {
            this.toggleVideo(false);
        }
        
        // Hide self view to be less conspicuous
        this.hideSelfView();
        
        // Ensure full-screen or focused mode
        this.optimizeViewMode();
    }

    toggleMicrophone(enable) {
        const micButton = this.findMicrophoneButton();
        if (micButton) {
            const isCurrentlyMuted = this.isMicrophoneMuted();
            
            if ((enable && isCurrentlyMuted) || (!enable && !isCurrentlyMuted)) {
                micButton.click();
                console.log(`Microphone ${enable ? 'enabled' : 'disabled'}`);
            }
        }
    }

    toggleVideo(enable) {
        const videoButton = this.findVideoButton();
        if (videoButton) {
            const isCurrentlyOff = this.isVideoOff();
            
            if ((enable && isCurrentlyOff) || (!enable && !isCurrentlyOff)) {
                videoButton.click();
                console.log(`Video ${enable ? 'enabled' : 'disabled'}`);
            }
        }
    }

    findMicrophoneButton() {
        const selectors = [
            '[data-is-muted]',
            '[aria-label*="microphone"]',
            '[aria-label*="Mute"]',
            '.mic-button',
            'button[data-tooltip*="microphone"]'
        ];
        
        return this.findElementBySelectors(selectors);
    }

    findVideoButton() {
        const selectors = [
            '[aria-label*="camera"]',
            '[aria-label*="video"]',
            '.video-button',
            'button[data-tooltip*="camera"]'
        ];
        
        return this.findElementBySelectors(selectors);
    }

    isMicrophoneMuted() {
        const micButton = this.findMicrophoneButton();
        if (micButton) {
            return micButton.getAttribute('data-is-muted') === 'true' ||
                   micButton.classList.contains('muted') ||
                   micButton.getAttribute('aria-pressed') === 'true';
        }
        return false;
    }

    isVideoOff() {
        const videoButton = this.findVideoButton();
        if (videoButton) {
            return videoButton.getAttribute('data-is-muted') === 'true' ||
                   videoButton.classList.contains('disabled') ||
                   videoButton.getAttribute('aria-pressed') === 'true';
        }
        return false;
    }

    hideSelfView() {
        const selfViewSelectors = [
            '[data-self-name]',
            '.self-view',
            '[aria-label*="You"]',
            '.participant-self'
        ];
        
        selfViewSelectors.forEach(selector => {
            const element = document.querySelector(selector);
            if (element && element.closest('.participant-container')) {
                element.closest('.participant-container').style.display = 'none';
            }
        });
    }

    optimizeViewMode() {
        // Try to enable speaker view or gallery view for better audio capture
        const viewButtons = document.querySelectorAll('[role="button"]');
        viewButtons.forEach(button => {
            const text = button.textContent || button.getAttribute('aria-label') || '';
            if (text.includes('Grid') || text.includes('Gallery')) {
                button.click();
            }
        });
    }

    sendParticipantInfo() {
        const participants = this.getParticipantList();
        this.sendMessage('PARTICIPANT_UPDATE', {
            count: participants.length,
            participants: participants
        });
    }

    getParticipantList() {
        const participants = [];
        const participantSelectors = [
            '[data-participant-id]',
            '.participant-name',
            '[aria-label*="participant"]'
        ];
        
        participantSelectors.forEach(selector => {
            const elements = document.querySelectorAll(selector);
            elements.forEach(element => {
                const name = this.extractParticipantName(element);
                if (name && !participants.some(p => p.name === name)) {
                    participants.push({
                        name: name,
                        id: element.getAttribute('data-participant-id') || Math.random().toString(36),
                        isHost: element.hasAttribute('data-is-host'),
                        isSelf: element.hasAttribute('data-self-name')
                    });
                }
            });
        });
        
        return participants;
    }

    extractParticipantName(element) {
        return element.textContent?.trim() ||
               element.getAttribute('data-name') ||
               element.getAttribute('aria-label')?.replace(/[^a-zA-Z\s]/g, '').trim();
    }

    findChatContainer() {
        const selectors = [
            '.chat-container',
            '.message-list',
            '[role="log"]',
            '.chat-messages'
        ];
        
        return this.findElementBySelectors(selectors);
    }

    isChatMessage(node) {
        const messageSelectors = [
            '.chat-message',
            '.message-item',
            '[data-message-id]'
        ];
        
        return messageSelectors.some(selector => 
            node.matches && node.matches(selector) || 
            node.querySelector && node.querySelector(selector)
        );
    }

    processChatMessage(messageNode) {
        const messageText = messageNode.textContent?.trim();
        const author = this.extractMessageAuthor(messageNode);
        
        if (messageText && author) {
            this.sendMessage('CHAT_MESSAGE', {
                text: messageText,
                author: author,
                timestamp: Date.now()
            });
        }
    }

    extractMessageAuthor(messageNode) {
        const authorSelectors = [
            '.message-author',
            '.sender-name',
            '[data-sender-name]'
        ];
        
        for (let selector of authorSelectors) {
            const authorElement = messageNode.querySelector(selector);
            if (authorElement) {
                return authorElement.textContent?.trim();
            }
        }
        
        return 'Unknown';
    }

    handleMeetingStateChange(selector, element) {
        switch (selector) {
            case '[data-call-ended]':
            case '.meeting-ended':
                this.sendMessage('MEETING_ENDED', { timestamp: Date.now() });
                this.cleanup();
                break;
                
            case '.connection-error':
                this.sendMessage('CONNECTION_ERROR', { timestamp: Date.now() });
                break;
                
            case '.rejoining':
                this.sendMessage('REJOINING', { timestamp: Date.now() });
                break;
        }
    }

    findElementBySelectors(selectors) {
        for (let selector of selectors) {
            const element = document.querySelector(selector);
            if (element) return element;
        }
        return null;
    }

    sendMessage(type, data) {
        if (this.port) {
            try {
                this.port.postMessage({ type, data });
            } catch (error) {
                console.error('Failed to send message to background:', error);
            }
        }
    }

    cleanup() {
        this.isActive = false;
        
        if (this.participantObserver) {
            this.participantObserver.disconnect();
        }
        
        if (this.chatObserver) {
            this.chatObserver.disconnect();
        }
        
        if (this.audioContext) {
            this.audioContext.close();
        }
        
        if (this.port) {
            this.port.disconnect();
        }
    }
}

// Initialize content script only on Google Meet pages
if (window.location.hostname === 'meet.google.com') {
    // Avoid multiple initializations
    if (!window.meetContentScript) {
        window.meetContentScript = new MeetContentScript();
    }
}

// Handle page navigation in SPA
let lastUrl = location.href;
new MutationObserver(() => {
    const url = location.href;
    if (url !== lastUrl) {
        lastUrl = url;
        if (window.meetContentScript) {
            window.meetContentScript.cleanup();
            window.meetContentScript = null;
        }
        
        if (url.includes('meet.google.com') && url.includes('/')) {
            setTimeout(() => {
                window.meetContentScript = new MeetContentScript();
            }, 1000);
        }
    }
}).observe(document, { subtree: true, childList: true });