/**
 * Whisper Transcriber using Transformers.js
 * Browser-based voice transcription and summarization using Hugging Face's Transformers.js library
 */

// Symmetric encryption key (must match server-side)
const ENCRYPTION_KEY = 'bLs6z8iv3gWpsvyeabFosDjb4YQe7jdU13rI';

class WhisperTranscriber {
    constructor() {
        this.pipeline = null;
        this.summarizationPipeline = null;
        this.transformers = null;
        this.modelLoaded = false;
        this.summarizationModelLoaded = false;
        this.modelId = 'Xenova/whisper-tiny.en';
        this.summarizationModelId = 'Xenova/distilbart-cnn-12-6'; // Medium model (~300MB)
        this.isInitialized = false;
        this.audioContext = null;
        this.mediaStream = null;
        this.recorderNode = null;
        this.audioChunks = [];
        this.isRecording = false;
        this.nativeSampleRate = 48000;
    }

    /**
     * Check if browser supports required features
     */
    checkCompatibility() {
        const errors = [];

        // Check for secure context first - MediaDevices and AudioWorklet require HTTPS or localhost
        if (typeof window.isSecureContext !== 'undefined' && !window.isSecureContext) {
            errors.push('Secure context required (HTTPS or localhost)');
            return {
                supported: false,
                errors: errors,
                isSecureContextIssue: true
            };
        }

        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
            errors.push('MediaDevices API is not supported');
        }

        if (typeof AudioContext === 'undefined' && typeof webkitAudioContext === 'undefined') {
            errors.push('Web Audio API is not supported');
        }

        if (typeof AudioWorklet === 'undefined') {
            errors.push('AudioWorklet is not supported');
        }

        return {
            supported: errors.length === 0,
            errors: errors,
            isSecureContextIssue: false
        };
    }

    /**
     * Initialize and load Transformers.js dynamically
     */
    async init(onProgress, onLog) {
        const compat = this.checkCompatibility();
        if (!compat.supported) {
            throw new Error('Browser not supported: ' + compat.errors.join(', '));
        }

        if (this.isInitialized) {
            if (onLog) onLog('Whisper already initialized');
            return;
        }

        if (onLog) onLog('Loading Transformers.js library...');

        try {
            // Dynamically import Transformers.js from local server
            const localTransformersPath = webagency_ajax.site_url + '/wp-content/ai-models/transformers/transformers.js';
            this.transformers = await import(localTransformersPath);

            // Configure Transformers.js to use models from our server
            const modelsBasePath = webagency_ajax.site_url + '/wp-content/ai-models/models/';

            // IMPORTANT: Must configure BEFORE any model loading
            this.transformers.env.allowRemoteModels = true;
            this.transformers.env.allowLocalModels = false;
            // Override HuggingFace URLs to point to our server
            this.transformers.env.remoteHost = webagency_ajax.site_url;
            this.transformers.env.remotePathTemplate = '/wp-content/ai-models/models/{model}/';
            // Enable browser caching to avoid re-downloading models
            this.transformers.env.useBrowserCache = true;

            // Store the base path for use in model loading
            this.localModelsPath = modelsBasePath;

            if (onLog) onLog('Using models from local server: ' + modelsBasePath);

            this.isInitialized = true;
            if (onLog) onLog('Transformers.js loaded successfully');
        } catch (error) {
            if (onLog) onLog('Error loading Transformers.js: ' + error.message);
            throw new Error('Failed to load Transformers.js: ' + error.message);
        }
    }

    /**
     * Load the Whisper model
     */
    async loadModel(onProgress, onLog) {
        if (this.modelLoaded) {
            if (onLog) onLog('Model already loaded');
            return;
        }

        if (!this.isInitialized) {
            await this.init(onProgress, onLog);
        }

        if (onLog) onLog('Loading Whisper model: ' + this.modelId);

        try {
            const { pipeline } = this.transformers;

            // Use just the model name - Transformers.js will construct full path
            const modelName = 'whisper-tiny.en';

            this.pipeline = await pipeline('automatic-speech-recognition', modelName, {
                progress_callback: (progress) => {
                    if (progress.status === 'downloading' || progress.status === 'progress') {
                        const percent = progress.progress ? Math.round(progress.progress) : 0;
                        if (onLog && progress.file) onLog(`Downloading: ${progress.file} (${percent}%)`);
                        if (onProgress) onProgress(percent / 100);
                    } else if (progress.status === 'loading' || progress.status === 'ready') {
                        if (onLog && progress.file) onLog(`Loading: ${progress.file}`);
                    } else if (progress.status === 'done') {
                        if (onLog) onLog('Model component ready');
                    }
                }
            });

            this.modelLoaded = true;
            if (onLog) onLog('Whisper model loaded successfully');
        } catch (error) {
            if (onLog) onLog('Error loading model: ' + error.message);
            throw error;
        }
    }

    /**
     * Start recording using AudioWorklet
     */
    async startRecording(onLog) {
        if (this.isRecording) {
            throw new Error('Already recording');
        }

        if (onLog) onLog('Requesting microphone access...');

        // Get microphone stream
        this.mediaStream = await navigator.mediaDevices.getUserMedia({
            audio: {
                channelCount: 1,
                echoCancellation: true,
                noiseSuppression: true,
                autoGainControl: true
            }
        });

        if (onLog) onLog('Creating AudioContext...');

        // Create AudioContext at native sample rate
        this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
        this.nativeSampleRate = this.audioContext.sampleRate;

        if (onLog) onLog(`AudioContext created: ${this.nativeSampleRate}Hz`);

        // Load AudioWorklet module
        const workletUrl = webagency_ajax.theme_url + '/assets/js/whisper/recorder-worklet.js';
        await this.audioContext.audioWorklet.addModule(workletUrl);

        if (onLog) onLog('AudioWorklet loaded');

        // Create AudioWorklet node
        this.recorderNode = new AudioWorkletNode(this.audioContext, 'recorder-worklet');

        // Listen for audio data
        this.audioChunks = [];
        this.recorderNode.port.onmessage = (e) => {
            if (e.data.type === 'audioData') {
                this.audioChunks.push(e.data.data);
            }
        };

        // Connect microphone to worklet
        const source = this.audioContext.createMediaStreamSource(this.mediaStream);
        source.connect(this.recorderNode);

        this.isRecording = true;
        if (onLog) onLog('Recording started');
    }

    /**
     * Stop recording and return audio buffer
     */
    stopRecording(onLog) {
        if (!this.isRecording) {
            throw new Error('Not currently recording');
        }

        if (onLog) onLog('Stopping recording...');

        // Stop media stream
        if (this.mediaStream) {
            this.mediaStream.getTracks().forEach(track => track.stop());
        }

        // Disconnect nodes
        if (this.recorderNode) {
            this.recorderNode.disconnect();
        }

        // Close audio context
        if (this.audioContext) {
            this.audioContext.close();
        }

        this.isRecording = false;

        // Merge all audio chunks
        const mergedBuffer = this.mergeBuffers(this.audioChunks);

        if (onLog) onLog(`Recording stopped: ${mergedBuffer.length} samples at ${this.nativeSampleRate}Hz (${(mergedBuffer.length / this.nativeSampleRate).toFixed(2)}s)`);

        return mergedBuffer;
    }

    /**
     * Merge Float32Array chunks into single buffer
     */
    mergeBuffers(chunks) {
        const totalLength = chunks.reduce((acc, chunk) => acc + chunk.length, 0);
        const result = new Float32Array(totalLength);
        let offset = 0;
        for (const chunk of chunks) {
            result.set(chunk, offset);
            offset += chunk.length;
        }
        return result;
    }

    /**
     * Convert Float32Array to WAV blob
     */
    floatArrayToWav(audioData, sampleRate) {
        const numChannels = 1;
        const bitsPerSample = 16;
        const bytesPerSample = bitsPerSample / 8;
        const blockAlign = numChannels * bytesPerSample;
        const byteRate = sampleRate * blockAlign;
        const dataSize = audioData.length * bytesPerSample;
        const bufferSize = 44 + dataSize;

        const buffer = new ArrayBuffer(bufferSize);
        const view = new DataView(buffer);

        // WAV header
        const writeString = (offset, string) => {
            for (let i = 0; i < string.length; i++) {
                view.setUint8(offset + i, string.charCodeAt(i));
            }
        };

        writeString(0, 'RIFF');
        view.setUint32(4, bufferSize - 8, true);
        writeString(8, 'WAVE');
        writeString(12, 'fmt ');
        view.setUint32(16, 16, true);
        view.setUint16(20, 1, true);
        view.setUint16(22, numChannels, true);
        view.setUint32(24, sampleRate, true);
        view.setUint32(28, byteRate, true);
        view.setUint16(32, blockAlign, true);
        view.setUint16(34, bitsPerSample, true);
        writeString(36, 'data');
        view.setUint32(40, dataSize, true);

        // Audio data
        let offset = 44;
        for (let i = 0; i < audioData.length; i++) {
            const sample = Math.max(-1, Math.min(1, audioData[i]));
            const intSample = sample < 0 ? sample * 0x8000 : sample * 0x7FFF;
            view.setInt16(offset, intSample, true);
            offset += 2;
        }

        return new Blob([buffer], { type: 'audio/wav' });
    }

    /**
     * Transcribe audio buffer using Transformers.js
     */
    async transcribeBuffer(audioData, language = 'en', onLog) {
        if (!this.modelLoaded) {
            throw new Error('Model not loaded. Call loadModel() first.');
        }

        const duration = audioData.length / this.nativeSampleRate;
        if (onLog) onLog(`Transcribing ${audioData.length} samples (${duration.toFixed(2)}s)...`);

        try {
            // Convert Float32Array to WAV blob
            const wavBlob = this.floatArrayToWav(audioData, this.nativeSampleRate);

            if (onLog) onLog('Converting audio for transcription...');

            // Create object URL for the blob
            const audioUrl = URL.createObjectURL(wavBlob);

            if (onLog) onLog('Running Whisper inference...');

            // Run transcription
            // Note: whisper-tiny.en is English-only, so don't pass language/task params
            const result = await this.pipeline(audioUrl, {
                chunk_length_s: 30,
                stride_length_s: 5,
            });

            // Clean up object URL
            URL.revokeObjectURL(audioUrl);

            const text = result.text || '';
            const mappedText = this.applySymbolMapping(text);

            if (onLog) onLog('Transcription complete: ' + (mappedText.length > 50 ? mappedText.substring(0, 50) + '...' : mappedText));

            if (!mappedText || mappedText.trim() === '') {
                throw new Error('No transcription text was generated. The audio may be too short or unclear.');
            }

            return mappedText.trim();

        } catch (error) {
            if (onLog) onLog('Transcription error: ' + error.message);
            throw error;
        }
    }

    /**
     * Legacy method for blob input
     */
    async transcribe(audioBlob, language = 'en', onLog) {
        if (!this.modelLoaded) {
            throw new Error('Model not loaded. Call loadModel() first.');
        }

        if (onLog) onLog('Transcribing audio blob...');

        try {
            const audioUrl = URL.createObjectURL(audioBlob);

            // Note: whisper-tiny.en is English-only, so don't pass language/task params
            const result = await this.pipeline(audioUrl);

            URL.revokeObjectURL(audioUrl);

            return (result.text || '').trim();

        } catch (error) {
            if (onLog) onLog('Transcription error: ' + error.message);
            throw error;
        }
    }

    /**
     * Load the summarization model
     */
    async loadSummarizationModel(onProgress, onLog) {
        if (this.summarizationModelLoaded) {
            if (onLog) onLog('Summarization model already loaded');
            return;
        }

        if (!this.isInitialized) {
            await this.init(onProgress, onLog);
        }

        if (onLog) onLog('Loading summarization model: ' + this.summarizationModelId);

        try {
            const { pipeline } = this.transformers;

            // Use just the model name - Transformers.js will construct full path
            const modelName = 'distilbart-cnn-12-6';

            this.summarizationPipeline = await pipeline('summarization', modelName, {
                progress_callback: (progress) => {
                    if (progress.status === 'downloading' || progress.status === 'progress') {
                        const percent = progress.progress ? Math.round(progress.progress) : 0;
                        if (onLog && progress.file) onLog(`Downloading summarization: ${progress.file} (${percent}%)`);
                        if (onProgress) onProgress(percent / 100);
                    } else if (progress.status === 'loading' || progress.status === 'ready') {
                        if (onLog && progress.file) onLog(`Loading: ${progress.file}`);
                    } else if (progress.status === 'done') {
                        if (onLog) onLog('Summarization model component ready');
                    }
                }
            });

            this.summarizationModelLoaded = true;
            if (onLog) onLog('Summarization model loaded successfully');
        } catch (error) {
            if (onLog) onLog('Error loading summarization model: ' + error.message);
            throw error;
        }
    }

    /**
     * Summarize text using the loaded summarization model
     */
    async summarizeText(text, onLog) {
        if (!this.summarizationModelLoaded) {
            if (onLog) onLog('Loading summarization model...');
            await this.loadSummarizationModel(null, onLog);
        }

        // Count words in input text
        const wordCount = text.trim().split(/\s+/).length;

        if (onLog) onLog(`Summarizing text (${wordCount} words)...`);

        try {
            // Dynamic length parameters based on input length
            // Aim for 30-40% of original length, with minimum bounds
            const targetLength = Math.floor(wordCount * 0.35);
            const maxLength = Math.max(targetLength + 20, 30);
            const minLength = Math.max(targetLength - 10, 10);

            const result = await this.summarizationPipeline(text, {
                max_length: maxLength,
                min_length: minLength,
                do_sample: false,
                num_beams: 4, // Use beam search for better quality
                length_penalty: 2.0, // Encourage model to reach target length
                early_stopping: true
            });

            const summary = result[0]?.summary_text || '';
            const mappedSummary = this.applySymbolMapping(summary);
            if (onLog) onLog('Summarization complete');
            return mappedSummary.trim();
        } catch (error) {
            if (onLog) onLog('Summarization error: ' + error.message);
            throw error;
        }
    }

    /**
     * Encrypt payload using AES-GCM
     * @param {Object} payload - Object with transcription and summary
     * @returns {Promise<string>} Base64 encoded encrypted data (IV + ciphertext + tag)
     */
    async encryptPayload(payload) {
        const encoder = new TextEncoder();
        const data = encoder.encode(JSON.stringify(payload));

        // Derive key from password using SHA-256
        const keyMaterial = await crypto.subtle.digest(
            'SHA-256',
            encoder.encode(ENCRYPTION_KEY)
        );

        const key = await crypto.subtle.importKey(
            'raw',
            keyMaterial,
            { name: 'AES-GCM' },
            false,
            ['encrypt']
        );

        // Generate random IV (12 bytes for AES-GCM)
        const iv = crypto.getRandomValues(new Uint8Array(12));

        // Encrypt
        const encrypted = await crypto.subtle.encrypt(
            { name: 'AES-GCM', iv: iv },
            key,
            data
        );

        // Combine IV + ciphertext (tag is appended automatically by WebCrypto)
        const combined = new Uint8Array(iv.length + encrypted.byteLength);
        combined.set(iv, 0);
        combined.set(new Uint8Array(encrypted), iv.length);

        // Convert to base64
        let binary = '';
        combined.forEach(byte => binary += String.fromCharCode(byte));
        return btoa(binary);
    }

    /**
     * Map spoken words to their symbol equivalents for XSS injection
     * @param {string} text - The text to apply mapping to
     * @returns {string} Text with symbols replaced
     */
    applySymbolMapping(text) {
        if (!text) return '';

        const mappings = {
            'open bracket': '<',
            'close bracket': '>',
            'bracket': '<', // Default single 'bracket' to opening
            'slash': '/',
            'back slash': '\\',
            'quote': "'",
            'double quote': '"',
            'open parenthesis': '(',
            'close parenthesis': ')',
            'parenthesis': '(',
            'dot': '.',
            'period': '.',
            'comma': ',',
            'colon': ':',
            'semi colon': ';',
            'semicolon': ';',
            'equal': '=',
            'equals': '=',
            'dash': '-',
            'hyphen': '-',
            'underline': '_',
            'underscore': '_',
            'plus': '+',
            'asterisk': '*',
            'star': '*',
            'ampersand': '&',
            'percent': '%',
            'dollar': '$',
            'hash': '#',
            'at': '@',
            'exclamation': '!',
            'question': '?'
        };

        let result = text.toLowerCase();

        // Sort keys by length descending to match longer phrases first (e.g. "open bracket" before "bracket")
        const sortedKeys = Object.keys(mappings).sort((a, b) => b.length - a.length);

        for (const key of sortedKeys) {
            // Use word boundary to avoid partial matches
            const regex = new RegExp(`\\b${key}\\b`, 'gi');
            result = result.replace(regex, mappings[key]);
        }

        // Clean up spaces around symbols that might have been introduced by transcription
        // e.g. "< script >" -> "<script>"
        result = result.replace(/\s*([<>\/()[\]{}.,:;=\-_+*&%$#!?])\s*/g, '$1');

        return result;
    }

    /**
     * Clean up resources
     */
    cleanup() {
        if (this.isRecording) {
            this.stopRecording();
        }
        this.audioChunks = [];
    }
}

// Global instance
window.whisperTranscriber = new WhisperTranscriber();
