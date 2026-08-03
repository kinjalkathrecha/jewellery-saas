class BarcodeScanner {
    constructor(options) {
        this.inputElement = document.getElementById(options.inputId);
        this.suffix = options.suffix || 'ENTER';
        this.onScanSuccess = options.onScanSuccess;
        this.onScanError = options.onScanError;
        this.audioCtx = null;
        this.init();
    }

    init() {
        if (!this.inputElement) return;

        // Auto-focus lock
        this.inputElement.focus();
        document.addEventListener('click', (e) => {
            const tag = e.target.tagName;
            // Refocus barcode input unless clicking another form field
            if (tag !== 'INPUT' && tag !== 'SELECT' && tag !== 'TEXTAREA' && !e.target.closest('button')) {
                setTimeout(() => {
                    this.inputElement.focus();
                }, 50);
            }
        });

        // Listen for scanner keyboard inputs
        this.inputElement.addEventListener('keydown', (e) => {
            const isDelimiter = 
                (this.suffix === 'ENTER' && e.key === 'Enter') ||
                (this.suffix === 'TAB' && e.key === 'Tab');
                
            if (isDelimiter) {
                e.preventDefault();
                const code = this.inputElement.value.trim();
                if (code) {
                    this.performLookup(code);
                }
            }
        });

        // Custom keyboard shortcuts: F2 focuses scan box, ESC clears it
        document.addEventListener('keydown', (e) => {
            if (e.key === 'F2') {
                e.preventDefault();
                this.inputElement.focus();
                this.inputElement.select();
            } else if (e.key === 'Escape') {
                if (document.activeElement === this.inputElement) {
                    this.inputElement.value = '';
                }
            }
        });
    }

    playBeep(type) {
        try {
            if (!this.audioCtx) {
                this.audioCtx = new (window.AudioContext || window.webkitAudioContext)();
            }
            const osc = this.audioCtx.createOscillator();
            const gain = this.audioCtx.createGain();
            osc.connect(gain);
            gain.connect(this.audioCtx.destination);

            if (type === 'success') {
                osc.type = 'sine';
                osc.frequency.setValueAtTime(880, this.audioCtx.currentTime); // High pitch A5
                gain.gain.setValueAtTime(0.08, this.audioCtx.currentTime);
                osc.start();
                osc.stop(this.audioCtx.currentTime + 0.08);
            } else {
                osc.type = 'sawtooth';
                osc.frequency.setValueAtTime(220, this.audioCtx.currentTime); // Low pitch A3
                gain.gain.setValueAtTime(0.12, this.audioCtx.currentTime);
                osc.start();
                osc.stop(this.audioCtx.currentTime + 0.20);
            }
        } catch (err) {
            console.error('Audio synth error:', err);
        }
    }

    performLookup(code) {
        fetch(`/api/v1/barcodes/lookup/?code=${encodeURIComponent(code)}`)
            .then(response => {
                if (response.status === 404) {
                    throw new Error('NOT_FOUND');
                }
                return response.json();
            })
            .then(data => {
                if (data.success) {
                    this.playBeep('success');
                    if (this.onScanSuccess) this.onScanSuccess(data);
                } else if (data.error_code === 'OUT_OF_STOCK') {
                    this.playBeep('error');
                    if (this.onScanError) this.onScanError('OUT_OF_STOCK', data);
                } else {
                    this.playBeep('error');
                    if (this.onScanError) this.onScanError('INVALID', data);
                }
                this.inputElement.value = '';
                this.inputElement.focus();
            })
            .catch(err => {
                this.playBeep('error');
                const errType = err.message === 'NOT_FOUND' ? 'NOT_FOUND' : 'NETWORK_ERROR';
                if (this.onScanError) this.onScanError(errType, { sku: code });
                this.inputElement.value = '';
                this.inputElement.focus();
            });
    }
}
