/**
 * Enterprise Google Meet Sentiment Bot - Popup Interface
 * Handles all popup interactions, API communication, and real-time updates
 */

class MeetSentimentBot {
    constructor() {
        this.apiUrl = 'http://localhost:8000';
        this.isConnected = false;
        this.sessionActive = false;
        this.startTime = null;
        this.durationInterval = null;
        this.statusInterval = null;
        this.config = {};
        
        this.init();
    }

    async init() {
        try {
            await this.loadConfiguration();
            this.setupEventListeners();
            this.initializeUI();
            await this.testConnection();
            this.startStatusUpdates();
            
            this.log('Bot initialized successfully', 'success');
        } catch (error) {
            this.log(`Initialization failed: ${error.message}`, 'error');
            console.error('Bot initialization error:', error);
        }
    }

    setupEventListeners() {
        // Configuration handlers
        $('#apiUrl').on('change', () => this.saveConfiguration());
        $('#emailAlert').on('change', () => this.saveConfiguration());
        $('#sentimentThreshold').on('change', () => this.saveConfiguration());
        
        // Control button handlers
        $('#testConnection').on('click', () => this.testConnection());
        $('#startBot').on('click', () => this.startBot());
        $('#stopBot').on('click', () => this.stopBot());
        $('#joinMeeting').on('click', () => this.joinMeeting());
        $('#detectMeeting').on('click', () => this.detectCurrentMeeting());
        
        // Advanced settings handlers
        $('input[type="checkbox"]').on('change', () => this.saveConfiguration());
        $('#recordingQuality').on('change', () => this.saveConfiguration());
        
        // Footer link handlers
        $('#openDashboard').on('click', (e) => {
            e.preventDefault();
            this.openDashboard();
        });
        
        $('#openLogs').on('click', (e) => {
            e.preventDefault();
            this.openLogs();
        });
        
        // Collapsible sections
        $('.collapsible-header').on('click', function() {
            $(this).closest('.collapsible').toggleClass('collapsed');
        });
        
        // Real-time meeting URL detection
        $('#meetingUrl').on('input', (e) => {
            const url = e.target.value;
            if (this.isValidMeetUrl(url)) {
                $('#joinMeeting').prop('disabled', false);
            } else {
                $('#joinMeeting').prop('disabled', true);
            }
        });
    }

    async loadConfiguration() {
        try {
            const result = await chrome.storage.sync.get([
                'apiUrl', 'emailAlert', 'sentimentThreshold', 'autoJoin',
                'muteOnJoin', 'disableVideo', 'enableLogging', 'recordingQuality'
            ]);
            
            this.config = {
                apiUrl: result.apiUrl || 'http://localhost:8000',
                emailAlert: result.emailAlert || '',
                sentimentThreshold: result.sentimentThreshold || '0.1',
                autoJoin: result.autoJoin !== false,
                muteOnJoin: result.muteOnJoin !== false,
                disableVideo: result.disableVideo !== false,
                enableLogging: result.enableLogging !== false,
                recordingQuality: result.recordingQuality || 'medium'
            };
            
            // Update UI with loaded configuration
            $('#apiUrl').val(this.config.apiUrl);
            $('#emailAlert').val(this.config.emailAlert);
            $('#sentimentThreshold').val(this.config.sentimentThreshold);
            $('#autoJoin').prop('checked', this.config.autoJoin);
            $('#muteOnJoin').prop('checked', this.config.muteOnJoin);
            $('#disableVideo').prop('checked', this.config.disableVideo);
            $('#enableLogging').prop('checked', this.config.enableLogging);
            $('#recordingQuality').val(this.config.recordingQuality);
            
            this.apiUrl = this.config.apiUrl;
            
        } catch (error) {
            console.error('Failed to load configuration:', error);
            this.log('Failed to load configuration', 'error');
        }
    }

    async saveConfiguration() {
        try {
            this.config = {
                apiUrl: $('#apiUrl').val(),
                emailAlert: $('#emailAlert').val(),
                sentimentThreshold: $('#sentimentThreshold').val(),
                autoJoin: $('#autoJoin').is(':checked'),
                muteOnJoin: $('#muteOnJoin').is(':checked'),
                disableVideo: $('#disableVideo').is(':checked'),
                enableLogging: $('#enableLogging').is(':checked'),
                recordingQuality: $('#recordingQuality').val()
            };
            
            await chrome.storage.sync.set(this.config);
            this.apiUrl = this.config.apiUrl;
            
            this.log('Configuration saved', 'success');
        } catch (error) {
            console.error('Failed to save configuration:', error);
            this.log('Failed to save configuration', 'error');
        }
    }

    initializeUI() {
        // Initialize collapsible sections
        $('.collapsible').addClass('collapsed');
        
        // Set initial button states
        this.updateButtonStates();
        
        // Add fade-in animation to sections
        $('.section').addClass('fade-in');
    }

    async testConnection() {
        this.showLoading('Testing connection...');
        
        try {
            const response = await this.apiCall('/health', 'GET');
            
            if (response.status === 'healthy') {
                this.isConnected = true;
                this.updateConnectionStatus(true);
                this.log('Connection successful', 'success');
            } else {
                throw new Error('Backend not healthy');
            }
        } catch (error) {
            this.isConnected = false;
            this.updateConnectionStatus(false);
            this.log(`Connection failed: ${error.message}`, 'error');
        } finally {
            this.hideLoading();
            this.updateButtonStates();
        }
    }

    async startBot() {
        if (!this.isConnected) {
            this.log('Please test connection first', 'warning');
            return;
        }

        this.showLoading('Starting bot...');
        
        try {
            const response = await this.apiCall('/bot/start', 'POST', {
                config: this.config,
                meetingUrl: $('#meetingUrl').val()
            });
            
            if (response.success) {
                this.sessionActive = true;
                this.startTime = new Date();
                this.startSessionTimer();
                this.updateButtonStates();
                this.log('Bot started successfully', 'success');
                
                // Start real-time updates
                this.startRealTimeUpdates();
            } else {
                throw new Error(response.error || 'Failed to start bot');
            }
        } catch (error) {
            this.log(`Failed to start bot: ${error.message}`, 'error');
        } finally {
            this.hideLoading();
        }
    }

    async stopBot() {
        this.showLoading('Stopping bot...');
        
        try {
            const response = await this.apiCall('/bot/stop', 'POST');
            
            if (response.success) {
                this.sessionActive = false;
                this.stopSessionTimer();
                this.stopRealTimeUpdates();
                this.resetSessionStats();
                this.updateButtonStates();
                this.log('Bot stopped successfully', 'success');
            } else {
                throw new Error(response.error || 'Failed to stop bot');
            }
        } catch (error) {
            this.log(`Failed to stop bot: ${error.message}`, 'error');
        } finally {
            this.hideLoading();
        }
    }

    async joinMeeting() {
        const meetingUrl = $('#meetingUrl').val();
        
        if (!this.isValidMeetUrl(meetingUrl)) {
            this.log('Please enter a valid Google Meet URL', 'warning');
            return;
        }

        this.showLoading('Joining meeting...');
        
        try {
            const response = await this.apiCall('/meeting/join', 'POST', {
                url: meetingUrl,
                config: this.config
            });
            
            if (response.success) {
                this.log('Successfully joined meeting', 'success');
                // Auto-start bot if configured
                if (this.config.autoJoin) {
                    setTimeout(() => this.startBot(), 2000);
                }
            } else {
                throw new Error(response.error || 'Failed to join meeting');
            }
        } catch (error) {
            this.log(`Failed to join meeting: ${error.message}`, 'error');
        } finally {
            this.hideLoading();
        }
    }

    async detectCurrentMeeting() {
        try {
            const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
            
            if (tab.url && tab.url.includes('meet.google.com')) {
                $('#meetingUrl').val(tab.url);
                $('#joinMeeting').prop('disabled', false);
                this.log('Meeting URL detected from current tab', 'success');
            } else {
                this.log('No Google Meet tab found', 'warning');
            }
        } catch (error) {
            this.log('Failed to detect meeting URL', 'error');
        }
    }

    startRealTimeUpdates() {
        this.statusInterval = setInterval(async () => {
            await this.updateSessionStatus();
        }, 2000);
    }

    stopRealTimeUpdates() {
        if (this.statusInterval) {
            clearInterval(this.statusInterval);
            this.statusInterval = null;
        }
    }

    async updateSessionStatus() {
        try {
            const response = await this.apiCall('/session/status', 'GET');
            
            if (response.success) {
                const status = response.data;
                
                // Update real-time metrics
                $('#currentSentiment').text(status.sentiment || '--');
                $('#participantCount').text(status.participants || '--');
                $('#alertsTriggered').text(status.alertsCount || '0');
                
                // Update sentiment color
                this.updateSentimentColor(status.sentiment);
                
                // Check for new alerts
                if (status.newAlert) {
                    this.handleNewAlert(status.newAlert);
                }
            }
        } catch (error) {
            console.error('Failed to update session status:', error);
        }
    }

    updateSentimentColor(sentiment) {
        const $sentimentElement = $('#currentSentiment');
        $sentimentElement.removeClass('text-success text-warning text-danger');
        
        if (sentiment !== null && sentiment !== '--') {
            const value = parseFloat(sentiment);
            if (value > 0.1) {
                $sentimentElement.addClass('text-success');
            } else if (value > -0.1) {
                $sentimentElement.addClass('text-warning');
            } else {
                $sentimentElement.addClass('text-danger');
            }
        }
    }

    handleNewAlert(alert) {
        // Show notification
        if (chrome.notifications) {
            chrome.notifications.create({
                type: 'basic',
                iconUrl: 'assets/images/icon-48.png',
                title: 'Sentiment Alert',
                message: alert.message
            });
        }
        
        this.log(`Alert: ${alert.message}`, 'warning');
    }

    startSessionTimer() {
        this.durationInterval = setInterval(() => {
            if (this.startTime) {
                const duration = new Date() - this.startTime;
                const minutes = Math.floor(duration / 60000);
                const seconds = Math.floor((duration % 60000) / 1000);
                $('#sessionDuration').text(`${minutes}:${seconds.toString().padStart(2, '0')}`);
            }
        }, 1000);
    }

    stopSessionTimer() {
        if (this.durationInterval) {
            clearInterval(this.durationInterval);
            this.durationInterval = null;
        }
    }

    resetSessionStats() {
        $('#currentSentiment').text('--').removeClass('text-success text-warning text-danger');
        $('#participantCount').text('--');
        $('#sessionDuration').text('--');
        this.startTime = null;
    }

    updateConnectionStatus(connected) {
        const $status = $('#connectionStatus');
        const $dot = $status.find('.status-dot');
        const $text = $status.find('.status-text');
        
        if (connected) {
            $dot.removeClass('offline').addClass('online');
            $text.text('Online');
        } else {
            $dot.removeClass('online').addClass('offline');
            $text.text('Offline');
        }
    }

    updateButtonStates() {
        const connectionReady = this.isConnected;
        const hasValidUrl = this.isValidMeetUrl($('#meetingUrl').val());
        
        $('#startBot').prop('disabled', !connectionReady || this.sessionActive);
        $('#stopBot').prop('disabled', !this.sessionActive);
        $('#joinMeeting').prop('disabled', !connectionReady || !hasValidUrl);
        $('#testConnection').prop('disabled', false);
    }

    isValidMeetUrl(url) {
        return url && url.includes('meet.google.com') && url.startsWith('https://');
    }

    async apiCall(endpoint, method = 'GET', data = null) {
        const url = `${this.apiUrl}${endpoint}`;
        const options = {
            method,
            headers: {
                'Content-Type': 'application/json',
                'X-Extension-Version': chrome.runtime.getManifest().version
            },
            credentials: 'include'
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

    startStatusUpdates() {
        // Periodic connection checks
        setInterval(() => {
            if (!this.sessionActive) {
                this.testConnection();
            }
        }, 30000);
    }

    showLoading(text = 'Processing...') {
        $('#loadingOverlay .loading-text').text(text);
        $('#loadingOverlay').addClass('show');
    }

    hideLoading() {
        $('#loadingOverlay').removeClass('show');
    }

    log(message, type = 'info') {
        const timestamp = new Date().toLocaleTimeString();
        const $logContainer = $('#activityLog');
        
        // Create log entry
        const $logEntry = $('<div class="activity-item"></div>');
        $logEntry.html(`
            <span class="activity-time">${timestamp}</span>
            <span class="activity-text ${type ? `text-${type}` : ''}">${message}</span>
        `);
        
        // Add to log (newest first)
        $logContainer.prepend($logEntry);
        
        // Keep only last 10 entries
        $logContainer.children().slice(10).remove();
        
        // Log to background script for persistence
        chrome.runtime.sendMessage({
            type: 'LOG_EVENT',
            data: { timestamp, message, type }
        });
    }

    openDashboard() {
        chrome.tabs.create({
            url: `${this.apiUrl}/dashboard`
        });
    }

    openLogs() {
        chrome.tabs.create({
            url: `${this.apiUrl}/logs`
        });
    }
}

// Initialize the bot when DOM is ready
$(document).ready(() => {
    window.meetBot = new MeetSentimentBot();
});

// Handle extension updates
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message.type === 'SESSION_UPDATE' && window.meetBot) {
        window.meetBot.updateSessionStatus();
    }
    
    if (message.type === 'CONNECTION_STATUS' && window.meetBot) {
        window.meetBot.updateConnectionStatus(message.connected);
    }
});