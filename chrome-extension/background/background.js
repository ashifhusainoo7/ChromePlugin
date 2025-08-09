/**
 * Enterprise Google Meet Sentiment Bot - Background Service Worker
 * Handles extension lifecycle, API communication, and message routing
 */

class BackgroundService {
    constructor() {
        this.apiUrl = 'http://localhost:8000';
        this.sessionId = null;
        this.isActive = false;
        this.logs = [];
        this.maxLogs = 1000;
        
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.loadConfiguration();
        this.setupPeriodicTasks();
        
        console.log('Background service initialized');
    }

    setupEventListeners() {
        // Extension installation/update
        chrome.runtime.onInstalled.addListener((details) => {
            this.handleInstallation(details);
        });

        // Extension startup
        chrome.runtime.onStartup.addListener(() => {
            this.handleStartup();
        });

        // Message handling
        chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
            this.handleMessage(message, sender, sendResponse);
            return true; // Keep channel open for async responses
        });

        // Tab updates (for meeting detection)
        chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
            this.handleTabUpdate(tabId, changeInfo, tab);
        });

        // External connections (from web pages)
        chrome.runtime.onConnectExternal.addListener((port) => {
            this.handleExternalConnection(port);
        });

        // Alarm handling for periodic tasks
        chrome.alarms.onAlarm.addListener((alarm) => {
            this.handleAlarm(alarm);
        });

        // Context menu setup
        this.setupContextMenus();
    }

    async loadConfiguration() {
        try {
            const config = await chrome.storage.sync.get(['apiUrl']);
            this.apiUrl = config.apiUrl || 'http://localhost:8000';
        } catch (error) {
            console.error('Failed to load configuration:', error);
        }
    }

    setupContextMenus() {
        chrome.contextMenus.create({
            id: 'joinMeeting',
            title: 'Join Meeting with Sentiment Bot',
            contexts: ['page', 'link'],
            documentUrlPatterns: ['*://meet.google.com/*']
        });

        chrome.contextMenus.onClicked.addListener((info, tab) => {
            if (info.menuItemId === 'joinMeeting') {
                this.handleContextMenuJoin(info, tab);
            }
        });
    }

    setupPeriodicTasks() {
        // Health check every 5 minutes
        chrome.alarms.create('healthCheck', { periodInMinutes: 5 });
        
        // Log cleanup every hour
        chrome.alarms.create('logCleanup', { periodInMinutes: 60 });
        
        // Session monitoring every 30 seconds when active
        chrome.alarms.create('sessionMonitor', { periodInMinutes: 0.5 });
    }

    async handleInstallation(details) {
        if (details.reason === 'install') {
            this.log('Extension installed', 'info');
            
            // Set default configuration
            await chrome.storage.sync.set({
                apiUrl: 'http://localhost:8000',
                sentimentThreshold: '0.1',
                autoJoin: true,
                muteOnJoin: true,
                disableVideo: true,
                enableLogging: true,
                recordingQuality: 'medium'
            });
            
            // Open welcome tab
            chrome.tabs.create({
                url: chrome.runtime.getURL('popup/popup.html')
            });
            
        } else if (details.reason === 'update') {
            this.log(`Extension updated to version ${chrome.runtime.getManifest().version}`, 'info');
        }
    }

    handleStartup() {
        this.log('Extension started', 'info');
        this.loadConfiguration();
    }

    async handleMessage(message, sender, sendResponse) {
        try {
            switch (message.type) {
                case 'LOG_EVENT':
                    this.handleLogEvent(message.data);
                    sendResponse({ success: true });
                    break;

                case 'START_SESSION':
                    const startResult = await this.startSession(message.data);
                    sendResponse(startResult);
                    break;

                case 'STOP_SESSION':
                    const stopResult = await this.stopSession();
                    sendResponse(stopResult);
                    break;

                case 'GET_STATUS':
                    const status = await this.getSessionStatus();
                    sendResponse(status);
                    break;

                case 'JOIN_MEETING':
                    const joinResult = await this.joinMeeting(message.data);
                    sendResponse(joinResult);
                    break;

                case 'GET_LOGS':
                    sendResponse({ logs: this.logs.slice(-100) });
                    break;

                case 'CLEAR_LOGS':
                    this.logs = [];
                    sendResponse({ success: true });
                    break;

                case 'HEALTH_CHECK':
                    const health = await this.performHealthCheck();
                    sendResponse(health);
                    break;

                default:
                    sendResponse({ error: 'Unknown message type' });
            }
        } catch (error) {
            console.error('Message handling error:', error);
            sendResponse({ error: error.message });
        }
    }

    handleTabUpdate(tabId, changeInfo, tab) {
        // Auto-detect Google Meet pages
        if (changeInfo.status === 'complete' && 
            tab.url && 
            tab.url.includes('meet.google.com')) {
            
            this.log(`Google Meet detected: ${tab.url}`, 'info');
            
            // Inject content script if needed
            this.injectContentScript(tabId);
            
            // Notify popup if open
            this.notifyPopup('MEETING_DETECTED', { url: tab.url, tabId });
        }
    }

    async injectContentScript(tabId) {
        try {
            await chrome.scripting.executeScript({
                target: { tabId },
                files: ['content/meet-content.js']
            });
        } catch (error) {
            console.error('Failed to inject content script:', error);
        }
    }

    handleExternalConnection(port) {
        if (port.name === 'meetingBot') {
            port.onMessage.addListener((message) => {
                this.handleExternalMessage(message, port);
            });
        }
    }

    handleAlarm(alarm) {
        switch (alarm.name) {
            case 'healthCheck':
                this.performHealthCheck();
                break;
            case 'logCleanup':
                this.cleanupLogs();
                break;
            case 'sessionMonitor':
                if (this.isActive) {
                    this.monitorSession();
                }
                break;
        }
    }

    async handleContextMenuJoin(info, tab) {
        try {
            const result = await this.joinMeeting({
                url: tab.url,
                tabId: tab.id
            });
            
            if (result.success) {
                this.showNotification('Meeting Join', 'Successfully joined the meeting!');
            } else {
                this.showNotification('Join Failed', result.error || 'Failed to join meeting');
            }
        } catch (error) {
            this.showNotification('Error', error.message);
        }
    }

    async startSession(data) {
        try {
            this.log('Starting bot session...', 'info');
            
            const response = await this.apiCall('/api/v1/session/start', 'POST', {
                meetingUrl: data.meetingUrl,
                config: data.config,
                sessionId: this.generateSessionId()
            });
            
            if (response.success) {
                this.sessionId = response.sessionId;
                this.isActive = true;
                this.log('Bot session started successfully', 'success');
                
                // Start monitoring
                this.startSessionMonitoring();
                
                return { success: true, sessionId: this.sessionId };
            } else {
                throw new Error(response.error || 'Failed to start session');
            }
        } catch (error) {
            this.log(`Failed to start session: ${error.message}`, 'error');
            return { success: false, error: error.message };
        }
    }

    async stopSession() {
        try {
            if (!this.sessionId) {
                return { success: false, error: 'No active session' };
            }
            
            this.log('Stopping bot session...', 'info');
            
            const response = await this.apiCall('/api/v1/session/stop', 'POST', {
                sessionId: this.sessionId
            });
            
            this.sessionId = null;
            this.isActive = false;
            this.stopSessionMonitoring();
            
            this.log('Bot session stopped', 'success');
            return { success: true };
            
        } catch (error) {
            this.log(`Failed to stop session: ${error.message}`, 'error');
            return { success: false, error: error.message };
        }
    }

    async getSessionStatus() {
        if (!this.sessionId || !this.isActive) {
            return { success: false, error: 'No active session' };
        }
        
        try {
            const response = await this.apiCall(`/api/v1/session/${this.sessionId}/status`, 'GET');
            return { success: true, data: response };
        } catch (error) {
            return { success: false, error: error.message };
        }
    }

    async joinMeeting(data) {
        try {
            this.log(`Joining meeting: ${data.url}`, 'info');
            
            const response = await this.apiCall('/api/v1/meeting/join', 'POST', {
                url: data.url,
                tabId: data.tabId,
                config: data.config
            });
            
            if (response.success) {
                this.log('Successfully joined meeting', 'success');
                return { success: true };
            } else {
                throw new Error(response.error || 'Failed to join meeting');
            }
        } catch (error) {
            this.log(`Failed to join meeting: ${error.message}`, 'error');
            return { success: false, error: error.message };
        }
    }

    async performHealthCheck() {
        try {
            const response = await this.apiCall('/api/v1/health', 'GET');
            const isHealthy = response.status === 'healthy';
            
            this.notifyPopup('CONNECTION_STATUS', { connected: isHealthy });
            
            return { success: true, healthy: isHealthy, data: response };
        } catch (error) {
            this.notifyPopup('CONNECTION_STATUS', { connected: false });
            return { success: false, healthy: false, error: error.message };
        }
    }

    startSessionMonitoring() {
        // Enable more frequent monitoring during active sessions
        chrome.alarms.clear('sessionMonitor');
        chrome.alarms.create('sessionMonitor', { periodInMinutes: 0.5 });
    }

    stopSessionMonitoring() {
        // Reduce monitoring frequency
        chrome.alarms.clear('sessionMonitor');
        chrome.alarms.create('sessionMonitor', { periodInMinutes: 5 });
    }

    async monitorSession() {
        if (!this.isActive || !this.sessionId) return;
        
        try {
            const status = await this.getSessionStatus();
            
            if (status.success) {
                // Check for alerts
                if (status.data.alerts && status.data.alerts.length > 0) {
                    status.data.alerts.forEach(alert => {
                        this.handleAlert(alert);
                    });
                }
                
                // Notify popup of updates
                this.notifyPopup('SESSION_UPDATE', status.data);
            }
        } catch (error) {
            console.error('Session monitoring error:', error);
        }
    }

    handleAlert(alert) {
        this.log(`Alert triggered: ${alert.message}`, 'warning');
        
        // Show notification
        this.showNotification(
            'Sentiment Alert',
            alert.message,
            alert.severity || 'normal'
        );
        
        // Send to popup
        this.notifyPopup('NEW_ALERT', alert);
    }

    async apiCall(endpoint, method = 'GET', data = null) {
        const url = `${this.apiUrl}${endpoint}`;
        const options = {
            method,
            headers: {
                'Content-Type': 'application/json',
                'X-Extension-Version': chrome.runtime.getManifest().version,
                'X-Session-ID': this.sessionId || ''
            }
        };

        if (data && method !== 'GET') {
            options.body = JSON.stringify(data);
        }

        const response = await fetch(url, options);
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        return await response.json();
    }

    notifyPopup(type, data) {
        // Try to send message to popup
        chrome.runtime.sendMessage({ type, data }).catch(() => {
            // Popup might not be open, that's fine
        });
    }

    showNotification(title, message, priority = 'normal') {
        chrome.notifications.create({
            type: 'basic',
            iconUrl: 'assets/images/icon-48.png',
            title,
            message,
            priority
        });
    }

    handleLogEvent(logData) {
        this.log(logData.message, logData.type);
    }

    log(message, type = 'info') {
        const logEntry = {
            timestamp: new Date().toISOString(),
            message,
            type,
            sessionId: this.sessionId
        };
        
        this.logs.push(logEntry);
        
        // Keep logs within limit
        if (this.logs.length > this.maxLogs) {
            this.logs = this.logs.slice(-this.maxLogs);
        }
        
        console.log(`[${type.toUpperCase()}] ${message}`);
    }

    cleanupLogs() {
        // Remove logs older than 24 hours
        const cutoff = new Date(Date.now() - 24 * 60 * 60 * 1000);
        this.logs = this.logs.filter(log => new Date(log.timestamp) > cutoff);
        
        this.log(`Log cleanup completed. ${this.logs.length} logs retained.`, 'info');
    }

    generateSessionId() {
        return `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }

    handleExternalMessage(message, port) {
        // Handle messages from injected content scripts or web pages
        switch (message.type) {
            case 'MEETING_JOINED':
                this.log('Meeting joined via content script', 'success');
                this.notifyPopup('MEETING_JOINED', message.data);
                break;
                
            case 'AUDIO_DATA':
                // Forward audio data to backend
                this.forwardAudioData(message.data);
                break;
                
            case 'PARTICIPANT_UPDATE':
                this.notifyPopup('PARTICIPANT_UPDATE', message.data);
                break;
        }
    }

    async forwardAudioData(audioData) {
        if (!this.sessionId) return;
        
        try {
            await this.apiCall('/api/v1/audio/process', 'POST', {
                sessionId: this.sessionId,
                audioData: audioData
            });
        } catch (error) {
            console.error('Failed to forward audio data:', error);
        }
    }
}

// Initialize the background service
const backgroundService = new BackgroundService();