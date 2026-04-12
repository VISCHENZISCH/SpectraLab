document.addEventListener('DOMContentLoaded', () => {
    const dropZone = document.getElementById('drop-zone-audio');
    const audioInput = document.getElementById('audio-input');
    const uploadPrompt = document.getElementById('upload-prompt');
    const audioImportZone = document.getElementById('audio-import-zone');
    const audioModeBtns = document.querySelectorAll('#audio-source-setup .source-mode-btn');
    const audioPanelImport = document.getElementById('audio-panel-import');
    const audioPanelRecord = document.getElementById('audio-panel-record');
    const previewContainer = document.getElementById('audio-preview-container');
    const removeBtn = document.getElementById('remove-audio');
    const convertBtn = document.getElementById('convert-audio-btn');
    const progressContainer = document.getElementById('progress-container');
    const progressFill = document.getElementById('progress-fill');
    const resultCard = document.getElementById('result-card');
    const transcriptionArea = document.getElementById('transcription-area');
    const transcriptionText = document.getElementById('transcription-text');
    const sttToggle = document.getElementById('stt-toggle');

    const pipelinePills = document.querySelectorAll('.pill');
    const pipelineViews = document.querySelectorAll('.pipeline-view');

    const playPauseBtn = document.getElementById('play-pause');
    const stopBtn = document.getElementById('stop-audio');
    const playIcon = document.getElementById('play-icon');
    const trimStart = document.getElementById('trim-start');
    const trimEnd = document.getElementById('trim-end');

    const micRecordBtn = document.getElementById('mic-record-btn');
    const micStopBtn = document.getElementById('mic-stop-btn');
    const micTimerEl = document.getElementById('mic-timer');
    const micMeterCanvas = document.getElementById('mic-meter');

    const voicePitch = document.getElementById('voice-pitch');
    const voicePitchVal = document.getElementById('voice-pitch-val');
    const voiceFormant = document.getElementById('voice-formant');
    const voiceFormantVal = document.getElementById('voice-formant-val');
    const voiceGrit = document.getElementById('voice-grit');
    const voicePreviewBtn = document.getElementById('voice-preview-btn');
    const voiceApplyBtn = document.getElementById('voice-apply-btn');
    const voicePresetBtns = document.querySelectorAll('.btn-voice-preset');

    pipelinePills.forEach((pill) => {
        pill.addEventListener('click', () => {
            const targetView = pill.getAttribute('data-view');
            pipelinePills.forEach((p) => p.classList.remove('active'));
            pill.classList.add('active');
            pipelineViews.forEach((view) => {
                if (view.id === `view-${targetView}`) view.classList.add('active');
                else view.classList.remove('active');
            });
        });
    });

    let selectedFile = null;
    let wavesurfer = null;
    let lastObjectUrl = null;
    let lastAudioBuffer = null;
    let currentVoicePreset = 'natural';

    let micStream = null;
    let micRecorder = null;
    let micChunks = [];
    let micRecordStart = 0;
    let micTimerId = null;
    let micAnalyser = null;
    let micAnalyserCtx = null;
    let micMeterRaf = null;

    let previewAudioCtx = null;
    let previewSourceNode = null;

    function setDropZoneSourceState(hasSource) {
        dropZone.classList.toggle('has-audio-source', hasSource);
    }

    function setAudioSourceMode(mode) {
        const isImport = mode === 'import';
        audioModeBtns.forEach((btn) => {
            const on = btn.getAttribute('data-mode') === mode;
            btn.classList.toggle('is-active', on);
            btn.setAttribute('aria-selected', on ? 'true' : 'false');
        });
        if (audioPanelImport) {
            audioPanelImport.classList.toggle('is-active', isImport);
        }
        if (audioPanelRecord) {
            audioPanelRecord.classList.toggle('is-active', !isImport);
        }
    }

    audioModeBtns.forEach((btn) => {
        btn.addEventListener('click', () => {
            if (selectedFile) return;
            setAudioSourceMode(btn.getAttribute('data-mode') || 'import');
        });
    });

    function revokeLastUrl() {
        if (lastObjectUrl) {
            URL.revokeObjectURL(lastObjectUrl);
            lastObjectUrl = null;
        }
    }

    async function decodeToBuffer(arrayBuffer) {
        const AC = window.AudioContext || window.webkitAudioContext;
        const ctx = new AC();
        try {
            return await ctx.decodeAudioData(arrayBuffer.slice(0));
        } finally {
            await ctx.close();
        }
    }

    async function cacheBufferFromFile(file) {
        try {
            const ab = await file.arrayBuffer();
            lastAudioBuffer = await decodeToBuffer(ab);
        } catch {
            lastAudioBuffer = null;
        }
    }

    function encodeWav(audioBuffer) {
        const numChannels = audioBuffer.numberOfChannels;
        const sampleRate = audioBuffer.sampleRate;
        const bitDepth = 16;
        const bytesPerSample = bitDepth / 8;
        const blockAlign = numChannels * bytesPerSample;
        const length = audioBuffer.length;
        const dataSize = length * blockAlign;
        const buffer = new ArrayBuffer(44 + dataSize);
        const view = new DataView(buffer);

        const writeStr = (off, s) => {
            for (let i = 0; i < s.length; i++) view.setUint8(off + i, s.charCodeAt(i));
        };

        writeStr(0, 'RIFF');
        view.setUint32(4, 36 + dataSize, true);
        writeStr(8, 'WAVE');
        writeStr(12, 'fmt ');
        view.setUint32(16, 16, true);
        view.setUint16(20, 1, true);
        view.setUint16(22, numChannels, true);
        view.setUint32(24, sampleRate, true);
        view.setUint32(28, sampleRate * blockAlign, true);
        view.setUint16(32, blockAlign, true);
        view.setUint16(34, bitDepth, true);
        writeStr(36, 'data');
        view.setUint32(40, dataSize, true);

        const chData = [];
        for (let c = 0; c < numChannels; c++) chData.push(audioBuffer.getChannelData(c));

        let offset = 44;
        for (let i = 0; i < length; i++) {
            for (let c = 0; c < numChannels; c++) {
                const s = Math.max(-1, Math.min(1, chData[c][i]));
                view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7fff, true);
                offset += 2;
            }
        }

        return new Blob([buffer], { type: 'audio/wav' });
    }

    function makeDistortionCurve(amount) {
        const n = 441;
        const curve = new Float32Array(n);
        const k = amount;
        for (let i = 0; i < n; i++) {
            const x = (i * 2) / n - 1;
            curve[i] = ((3 + k) * x * 20 * Math.PI) / (Math.PI + k * Math.abs(x));
        }
        return curve;
    }

    function wireVoiceEffects(ctx, source, preset, formantNorm, gritOn) {
        let node = source;

        const hp = ctx.createBiquadFilter();
        hp.type = 'highpass';
        hp.frequency.value = preset === 'phone' ? 320 : 28;
        node.connect(hp);
        node = hp;

        const peak = ctx.createBiquadFilter();
        peak.type = 'peaking';
        peak.frequency.value = 500 + formantNorm * 48;
        peak.Q = 1.15;
        peak.gain.value = -5 + formantNorm * 12;
        node.connect(peak);
        node = peak;

        const lp = ctx.createBiquadFilter();
        lp.type = 'lowpass';
        lp.frequency.value = preset === 'phone' ? 3200 : 15000 - formantNorm * 95;
        node.connect(lp);
        node = lp;

        if (gritOn || preset === 'robot') {
            const sh = ctx.createWaveShaper();
            sh.curve = makeDistortionCurve(preset === 'robot' ? 520 : 280);
            sh.oversample = '4x';
            node.connect(sh);
            node = sh;
        }

        const gain = ctx.createGain();
        gain.gain.value = 0.94;
        node.connect(gain);
        return gain;
    }

    function stopPreviewPlayback() {
        if (previewSourceNode) {
            try {
                previewSourceNode.stop();
            } catch {
                /* ignore */
            }
            previewSourceNode.disconnect();
            previewSourceNode = null;
        }
        if (previewAudioCtx) {
            previewAudioCtx.close().catch(() => {});
            previewAudioCtx = null;
        }
    }

    function updateVoiceLabels() {
        if (voicePitchVal && voicePitch) voicePitchVal.textContent = voicePitch.value;
        if (voiceFormantVal && voiceFormant) voiceFormantVal.textContent = voiceFormant.value;
    }

    voicePitch?.addEventListener('input', updateVoiceLabels);
    voiceFormant?.addEventListener('input', updateVoiceLabels);
    updateVoiceLabels();

    voicePresetBtns.forEach((btn) => {
        btn.addEventListener('click', () => {
            voicePresetBtns.forEach((b) => b.classList.remove('is-active'));
            btn.classList.add('is-active');
            const preset = btn.getAttribute('data-preset') || 'natural';
            currentVoicePreset = preset;
            if (voiceGrit) voiceGrit.checked = preset === 'robot';
            if (!voicePitch || !voiceFormant) return;
            if (preset === 'natural') {
                voicePitch.value = '0';
                voiceFormant.value = '50';
            } else if (preset === 'deep') {
                voicePitch.value = '-5';
                voiceFormant.value = '32';
            } else if (preset === 'bright') {
                voicePitch.value = '5';
                voiceFormant.value = '68';
            } else if (preset === 'robot') {
                voicePitch.value = '0';
                voiceFormant.value = '55';
            } else if (preset === 'phone') {
                voicePitch.value = '0';
                voiceFormant.value = '45';
            }
            updateVoiceLabels();
        });
    });
    voicePresetBtns[0]?.classList.add('is-active');

    async function renderTransformedBuffer(inputBuffer) {
        const semitones = parseFloat(voicePitch?.value || '0');
        const formantNorm = parseFloat(voiceFormant?.value || '50') / 100;
        const grit = !!voiceGrit?.checked;

        const offline = new OfflineAudioContext(
            inputBuffer.numberOfChannels,
            inputBuffer.length,
            inputBuffer.sampleRate
        );
        const src = offline.createBufferSource();
        src.buffer = inputBuffer;
        src.detune.value = semitones * 100;
        const tail = wireVoiceEffects(offline, src, currentVoicePreset, formantNorm, grit);
        tail.connect(offline.destination);
        src.start(0);
        return offline.startRendering();
    }

    voicePreviewBtn?.addEventListener('click', async () => {
        if (!lastAudioBuffer) {
            alert('Importez ou enregistrez un audio avant d’écouter la transformation.');
            return;
        }
        stopPreviewPlayback();
        const AC = window.AudioContext || window.webkitAudioContext;
        previewAudioCtx = new AC();
        const src = previewAudioCtx.createBufferSource();
        src.buffer = lastAudioBuffer;
        src.detune.value = parseFloat(voicePitch?.value || '0') * 100;
        const tail = wireVoiceEffects(
            previewAudioCtx,
            src,
            currentVoicePreset,
            parseFloat(voiceFormant?.value || '50') / 100,
            !!voiceGrit?.checked
        );
        tail.connect(previewAudioCtx.destination);
        previewSourceNode = src;
        src.onended = () => {
            previewSourceNode = null;
            if (previewAudioCtx) {
                previewAudioCtx.close().catch(() => {});
                previewAudioCtx = null;
            }
        };
        try {
            await previewAudioCtx.resume();
            src.start(0);
        } catch (err) {
            console.error(err);
            alert('Lecture impossible. Vérifiez les permissions audio du navigateur.');
        }
    });

    voiceApplyBtn?.addEventListener('click', async () => {
        if (!lastAudioBuffer) {
            alert('Aucune piste à transformer.');
            return;
        }
        stopPreviewPlayback();
        voiceApplyBtn.disabled = true;
        try {
            const rendered = await renderTransformedBuffer(lastAudioBuffer);
            const wavBlob = encodeWav(rendered);
            revokeLastUrl();
            lastObjectUrl = URL.createObjectURL(wavBlob);
            selectedFile = new File([wavBlob], 'voix-transformee.wav', { type: 'audio/wav' });
            lastAudioBuffer = rendered;
            if (wavesurfer) wavesurfer.destroy();
            initWaveSurfer();
            await wavesurfer.load(lastObjectUrl);
            uploadPrompt.style.display = 'none';
            previewContainer.style.display = 'block';
            setDropZoneSourceState(true);
            lucide.createIcons();
        } catch (err) {
            console.error(err);
            alert('Échec du rendu audio. Réessayez avec un clip plus court.');
        } finally {
            voiceApplyBtn.disabled = false;
        }
    });

    const initWaveSurfer = () => {
        if (wavesurfer) wavesurfer.destroy();
        wavesurfer = WaveSurfer.create({
            container: '#waveform',
            waveColor: 'rgba(61, 255, 156, 0.25)',
            progressColor: '#3dff9c',
            cursorColor: '#3dff9c',
            barWidth: 2,
            barRadius: 3,
            height: 120,
        });

        wavesurfer.on('play', () => {
            playIcon?.setAttribute('data-lucide', 'pause');
            lucide.createIcons();
        });
        wavesurfer.on('pause', () => {
            playIcon?.setAttribute('data-lucide', 'play');
            lucide.createIcons();
        });
        wavesurfer.on('ready', () => {
            if (trimStart) trimStart.value = 0;
            if (trimEnd) trimEnd.value = wavesurfer.getDuration().toFixed(1);
        });
    };

    const formatButtonsNew = document.querySelectorAll('.btn-format');
    formatButtonsNew.forEach((btn) => {
        btn.addEventListener('click', () => {
            const card = btn.closest('.format-selection-card');
            if (!card) return;
            card.querySelectorAll('.btn-format').forEach((b) => b.classList.remove('active'));
            btn.classList.add('active');
        });
    });

    audioImportZone?.addEventListener('click', () => {
        if (!selectedFile) audioInput.click();
    });
    audioImportZone?.addEventListener('dragover', (e) => {
        e.preventDefault();
        e.stopPropagation();
    });
    audioImportZone?.addEventListener('drop', (e) => {
        e.preventDefault();
        e.stopPropagation();
        const f = e.dataTransfer?.files?.[0];
        if (f && f.type.startsWith('audio/')) handleFile(f);
    });
    audioInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) handleFile(e.target.files[0]);
    });

    async function handleFile(file) {
        if (!file.type.startsWith('audio/')) return alert('Audio invalide');
        setAudioSourceMode('import');
        stopMicMeter();
        stopAllCaptureStreams();
        selectedFile = file;
        revokeLastUrl();
        lastObjectUrl = URL.createObjectURL(file);
        uploadPrompt.style.display = 'none';
        previewContainer.style.display = 'block';
        setDropZoneSourceState(true);
        initWaveSurfer();
        wavesurfer.load(lastObjectUrl);
        await cacheBufferFromFile(file);
    }

    async function handleRecordedBlob(blob, filename) {
        if (!blob.size) return alert('Enregistrement vide.');
        setAudioSourceMode('record');
        stopMicMeter();
        const file = new File([blob], filename, { type: blob.type || 'audio/webm' });
        selectedFile = file;
        revokeLastUrl();
        lastObjectUrl = URL.createObjectURL(blob);
        uploadPrompt.style.display = 'none';
        previewContainer.style.display = 'block';
        setDropZoneSourceState(true);
        initWaveSurfer();
        try {
            await wavesurfer.load(lastObjectUrl);
        } catch {
            alert('Format non lu par le lecteur. Essayez Chrome / Edge ou un enregistrement plus court.');
            return;
        }
        await cacheBufferFromFile(file);
    }

    playPauseBtn?.addEventListener('click', (e) => {
        e.stopPropagation();
        if (wavesurfer) wavesurfer.playPause();
    });
    stopBtn?.addEventListener('click', (e) => {
        e.stopPropagation();
        if (wavesurfer) wavesurfer.stop();
    });

    removeBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        stopPreviewPlayback();
        stopMicMeter();
        stopAllCaptureStreams();
        if (wavesurfer) wavesurfer.stop();
        selectedFile = null;
        lastAudioBuffer = null;
        revokeLastUrl();
        uploadPrompt.style.display = 'flex';
        previewContainer.style.display = 'none';
        resultCard.style.display = 'none';
        transcriptionArea.style.display = 'none';
        setDropZoneSourceState(false);
        setAudioSourceMode('import');
    });

    function pickMime(preferredList) {
        for (const t of preferredList) {
            if (MediaRecorder.isTypeSupported(t)) return t;
        }
        return '';
    }

    function stopAllCaptureStreams() {
        if (micStream) {
            micStream.getTracks().forEach((t) => t.stop());
            micStream = null;
        }
    }

    function formatRecTime(ms) {
        const s = Math.floor(ms / 1000);
        const m = Math.floor(s / 60);
        const r = s % 60;
        return `${String(m).padStart(2, '0')}:${String(r).padStart(2, '0')}`;
    }

    function stopMicMeter() {
        if (micMeterRaf) cancelAnimationFrame(micMeterRaf);
        micMeterRaf = null;
        if (micAnalyserCtx) {
            micAnalyserCtx.close().catch(() => {});
            micAnalyserCtx = null;
        }
        micAnalyser = null;
        const ctx2d = micMeterCanvas?.getContext('2d');
        if (ctx2d && micMeterCanvas) {
            ctx2d.clearRect(0, 0, micMeterCanvas.width, micMeterCanvas.height);
        }
    }

    function drawMicMeter() {
        if (!micAnalyser || !micMeterCanvas) return;
        const ctx2d = micMeterCanvas.getContext('2d');
        const w = micMeterCanvas.width;
        const h = micMeterCanvas.height;
        const data = new Uint8Array(micAnalyser.frequencyBinCount);
        micAnalyser.getByteFrequencyData(data);
        ctx2d.fillStyle = 'rgba(0,0,0,0.2)';
        ctx2d.fillRect(0, 0, w, h);
        const bars = 48;
        const step = Math.floor(data.length / bars);
        for (let i = 0; i < bars; i++) {
            let v = 0;
            for (let j = 0; j < step; j++) v += data[i * step + j];
            v /= step;
            const bh = (v / 255) * (h - 4);
            ctx2d.fillStyle = `rgba(61, 255, 156, ${0.25 + (v / 255) * 0.75})`;
            ctx2d.fillRect(4 + i * ((w - 8) / bars), h - bh - 2, Math.max(1, (w - 8) / bars - 1), bh);
        }
        micMeterRaf = requestAnimationFrame(drawMicMeter);
    }

    micRecordBtn?.addEventListener('click', async () => {
        try {
            stopPreviewPlayback();
            stopAllCaptureStreams();
            micStream = await navigator.mediaDevices.getUserMedia({
                audio: { echoCancellation: true, noiseSuppression: true },
                video: false,
            });
            micChunks = [];
            const mime = pickMime(['audio/webm;codecs=opus', 'audio/webm', 'audio/mp4']);
            micRecorder = mime ? new MediaRecorder(micStream, { mimeType: mime }) : new MediaRecorder(micStream);
            micRecorder.ondataavailable = (ev) => {
                if (ev.data.size) micChunks.push(ev.data);
            };
            micRecorder.onstop = async () => {
                const blob = new Blob(micChunks, { type: micRecorder.mimeType || 'audio/webm' });
                micRecordBtn.disabled = false;
                micStopBtn.disabled = true;
                clearInterval(micTimerId);
                stopMicMeter();
                if (micStream) {
                    micStream.getTracks().forEach((t) => t.stop());
                    micStream = null;
                }
                await handleRecordedBlob(blob, 'enregistrement-micro.webm');
            };
            const AC = window.AudioContext || window.webkitAudioContext;
            micAnalyserCtx = new AC();
            const src = micAnalyserCtx.createMediaStreamSource(micStream);
            micAnalyser = micAnalyserCtx.createAnalyser();
            micAnalyser.fftSize = 256;
            src.connect(micAnalyser);
            await micAnalyserCtx.resume();
            drawMicMeter();

            micRecorder.start(200);
            micRecordStart = Date.now();
            micTimerEl.textContent = '00:00';
            micTimerId = setInterval(() => {
                micTimerEl.textContent = formatRecTime(Date.now() - micRecordStart);
            }, 500);
            micRecordBtn.disabled = true;
            micStopBtn.disabled = false;
        } catch (err) {
            console.error(err);
            alert('Micro inaccessible. Vérifiez les permissions du navigateur.');
        }
    });

    micStopBtn?.addEventListener('click', () => {
        if (micRecorder && micRecorder.state !== 'inactive') micRecorder.stop();
    });

    convertBtn.addEventListener('click', () => {
        if (!selectedFile) return alert('Importez ou enregistrez un audio');

        resultCard.style.display = 'none';
        transcriptionArea.style.display = 'none';
        if (progressContainer) progressContainer.style.display = 'block';
        if (progressFill) progressFill.style.width = '0%';
        convertBtn.disabled = true;

        let progress = 0;
        const interval = setInterval(() => {
            progress += Math.random() * 20;
            if (progress >= 100) {
                progress = 100;
                clearInterval(interval);

                setTimeout(() => {
                    if (progressContainer) progressContainer.style.display = 'none';
                    resultCard.style.display = 'block';

                    if (sttToggle?.checked) {
                        transcriptionArea.style.display = 'block';
                        transcriptionText.value =
                            "Ceci est une simulation de transcription IA...\n\nL'audio analysé semble contenir une voix masculine parlant de technologie et de design minimaliste. La qualité sonore est excellente.";
                    }

                    convertBtn.disabled = false;
                    window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' });
                }, 500);
            }
            if (progressFill) progressFill.style.width = `${progress}%`;
        }, 400);
    });

    lucide.createIcons();
});
