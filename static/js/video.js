document.addEventListener('DOMContentLoaded', () => {
    const dropZone = document.getElementById('drop-zone-video');
    const videoInput = document.getElementById('video-input');
    const videoImportZone = document.getElementById('video-import-zone');
    const videoModeBtns = document.querySelectorAll('#video-source-setup .source-mode-btn');
    const videoPanelImport = document.getElementById('video-panel-import');
    const videoPanelRecord = document.getElementById('video-panel-record');
    const uploadPrompt = document.getElementById('upload-prompt');
    const previewContainer = document.getElementById('video-preview-container');
    const videoPreview = document.getElementById('video-preview');
    const removeBtn = document.getElementById('remove-video');
    const convertBtn = document.getElementById('convert-video-btn');
    const choiceButtons = document.querySelectorAll('.btn-format');

    const cameraRecordPreview = document.getElementById('camera-record-preview');
    const studioVideoRecordBtn = document.getElementById('studio-video-record-btn');
    const studioVideoStopBtn = document.getElementById('studio-video-stop-btn');
    const studioVideoTimerEl = document.getElementById('studio-video-timer');

    const pipelinePills = document.querySelectorAll('.pill');
    const pipelineViews = document.querySelectorAll('.pipeline-view');

    let selectedFile = null;
    let lastVideoObjectUrl = null;
    let studioStream = null;
    let studioRecorder = null;
    let studioChunks = [];
    let studioRecordStart = 0;
    let studioTimerId = null;

    function revokeVideoUrl() {
        if (lastVideoObjectUrl) {
            URL.revokeObjectURL(lastVideoObjectUrl);
            lastVideoObjectUrl = null;
        }
    }

    function setVideoSourceMode(mode) {
        const isImport = mode === 'import';
        videoModeBtns.forEach((btn) => {
            const on = btn.getAttribute('data-mode') === mode;
            btn.classList.toggle('is-active', on);
            btn.setAttribute('aria-selected', on ? 'true' : 'false');
        });
        if (videoPanelImport) videoPanelImport.classList.toggle('is-active', isImport);
        if (videoPanelRecord) videoPanelRecord.classList.toggle('is-active', !isImport);
    }

    videoModeBtns.forEach((btn) => {
        btn.addEventListener('click', () => {
            if (selectedFile) return;
            setVideoSourceMode(btn.getAttribute('data-mode') || 'import');
        });
    });

    function stopStudioCapture() {
        if (studioStream) {
            studioStream.getTracks().forEach((t) => t.stop());
            studioStream = null;
        }
        if (cameraRecordPreview) cameraRecordPreview.srcObject = null;
    }

    function pickMime(preferredList) {
        for (const t of preferredList) {
            if (MediaRecorder.isTypeSupported(t)) return t;
        }
        return '';
    }

    function formatRecTime(ms) {
        const s = Math.floor(ms / 1000);
        const m = Math.floor(s / 60);
        const r = s % 60;
        return `${String(m).padStart(2, '0')}:${String(r).padStart(2, '0')}`;
    }

    pipelinePills.forEach(pill => {
        pill.addEventListener('click', () => {
            const targetView = pill.getAttribute('data-view');

            // Update pills
            pipelinePills.forEach(p => p.classList.remove('active'));
            pill.classList.add('active');

            // Update views
            pipelineViews.forEach(view => {
                if (view.id === `view-${targetView}`) {
                    view.classList.add('active');
                } else {
                    view.classList.remove('active');
                }
            });
        });
    });

    // UI Feedback
    const progressContainer = document.getElementById('progress-container');
    const progressFill = document.getElementById('progress-fill');
    const resultCard = document.getElementById('result-card');

    const formatButtonsNew = document.querySelectorAll('.btn-format');
    formatButtonsNew.forEach(btn => {
        btn.addEventListener('click', () => {
            const card = btn.closest('.format-selection-card');
            if (!card) return;
            card.querySelectorAll('.btn-format').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
        });
    });

    videoImportZone?.addEventListener('click', () => {
        if (!selectedFile) videoInput.click();
    });
    videoImportZone?.addEventListener('dragover', (e) => {
        e.preventDefault();
        e.stopPropagation();
    });
    videoImportZone?.addEventListener('drop', (e) => {
        e.preventDefault();
        e.stopPropagation();
        const f = e.dataTransfer?.files?.[0];
        if (f && f.type.startsWith('video/')) handleFile(f);
    });
    videoInput.addEventListener('change', (e) => { if (e.target.files.length > 0) handleFile(e.target.files[0]); });

    function applyVideoToPreview(file) {
        revokeVideoUrl();
        lastVideoObjectUrl = URL.createObjectURL(file);
        selectedFile = file;
        uploadPrompt.style.display = 'none';
        previewContainer.style.display = 'block';
        dropZone.classList.add('has-video-source');
        videoPreview.src = lastVideoObjectUrl;
        videoPreview.onloadedmetadata = () => {
            document.getElementById('trim-start-sidebar').value = 0;
            document.getElementById('trim-end-sidebar').value = Math.floor(videoPreview.duration);
            document.getElementById('total-time').textContent = formatTime(videoPreview.duration);
        };
        initScannerForVideo(file);
    }

    function handleFile(file) {
        if (!file.type.startsWith('video/')) return alert('Vidéo invalide');
        setVideoSourceMode('import');
        stopStudioCapture();
        applyVideoToPreview(file);
    }

    async function handleRecordedVideo(blob) {
        if (!blob.size) return alert('Enregistrement vide.');
        stopStudioCapture();
        const file = new File([blob], 'enregistrement-studio.webm', { type: blob.type || 'video/webm' });
        setVideoSourceMode('record');
        applyVideoToPreview(file);
    }

    studioVideoRecordBtn?.addEventListener('click', async () => {
        try {
            stopStudioCapture();
            studioStream = await navigator.mediaDevices.getUserMedia({
                audio: true,
                video: { facingMode: 'user', width: { ideal: 1280 }, height: { ideal: 720 } },
            });
            if (cameraRecordPreview) {
                cameraRecordPreview.srcObject = studioStream;
                await cameraRecordPreview.play();
            }
            studioChunks = [];
            const mime = pickMime(['video/webm;codecs=vp9,opus', 'video/webm;codecs=vp8,opus', 'video/webm']);
            studioRecorder = mime ? new MediaRecorder(studioStream, { mimeType: mime }) : new MediaRecorder(studioStream);
            studioRecorder.ondataavailable = (ev) => {
                if (ev.data.size) studioChunks.push(ev.data);
            };
            studioRecorder.onstop = async () => {
                const blob = new Blob(studioChunks, { type: studioRecorder.mimeType || 'video/webm' });
                studioVideoRecordBtn.disabled = false;
                studioVideoStopBtn.disabled = true;
                clearInterval(studioTimerId);
                stopStudioCapture();
                await handleRecordedVideo(blob);
            };
            studioRecorder.start(250);
            studioRecordStart = Date.now();
            if (studioVideoTimerEl) studioVideoTimerEl.textContent = '00:00';
            studioTimerId = setInterval(() => {
                if (studioVideoTimerEl) studioVideoTimerEl.textContent = formatRecTime(Date.now() - studioRecordStart);
            }, 500);
            studioVideoRecordBtn.disabled = true;
            studioVideoStopBtn.disabled = false;
        } catch (err) {
            console.error(err);
            alert('Caméra ou micro inaccessible. Utilisez HTTPS / localhost et autorisez l’accès.');
        }
    });

    studioVideoStopBtn?.addEventListener('click', () => {
        if (studioRecorder && studioRecorder.state !== 'inactive') studioRecorder.stop();
    });

    // Custom Video Controls
    const playPauseBtn = document.getElementById('video-play-pause');
    const progressBar = document.getElementById('video-progress-bar');
    const currentTimeEl = document.getElementById('current-time');
    const videoSeeker = document.getElementById('video-seeker');

    playPauseBtn.addEventListener('click', () => {
        if (videoPreview.paused) {
            videoPreview.play();
            playPauseBtn.innerHTML = '<i data-lucide="pause" size="20"></i>';
        } else {
            videoPreview.pause();
            playPauseBtn.innerHTML = '<i data-lucide="play" size="20"></i>';
        }
        lucide.createIcons();
    });

    videoPreview.addEventListener('timeupdate', () => {
        const progress = (videoPreview.currentTime / videoPreview.duration) * 100;
        progressBar.style.width = `${progress}%`;
        currentTimeEl.textContent = formatTime(videoPreview.currentTime);
        syncScannerPlayhead();
    });

    videoSeeker.addEventListener('click', (e) => {
        const rect = videoSeeker.getBoundingClientRect();
        const pos = (e.clientX - rect.left) / rect.width;
        videoPreview.currentTime = pos * videoPreview.duration;
    });

    function formatTime(seconds) {
        const min = Math.floor(seconds / 60);
        const sec = Math.floor(seconds % 60);
        return `${min.toString().padStart(2, '0')}:${sec.toString().padStart(2, '0')}`;
    }

    removeBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        stopStudioCapture();
        selectedFile = null;
        videoPreview.src = '';
        revokeVideoUrl();
        uploadPrompt.style.display = 'flex';
        previewContainer.style.display = 'none';
        resultCard.style.display = 'none';
        dropZone.classList.remove('has-video-source');
        setVideoSourceMode('import');
        resetScannerUi();
    });

    // Action: Video Rendering
    convertBtn.addEventListener('click', () => {
        if (!selectedFile) return alert('Importez ou enregistrez une vidéo');

        resultCard.style.display = 'none';
        if (progressContainer) progressContainer.style.display = 'block';
        if (progressFill) progressFill.style.width = '0%';
        convertBtn.disabled = true;

        let progress = 0;
        const interval = setInterval(() => {
            progress += Math.random() * 15; // Un peu plus lent car encodage vidéo
            if (progress >= 100) {
                progress = 100;
                clearInterval(interval);

                setTimeout(() => {
                    if (progressContainer) progressContainer.style.display = 'none';
                    resultCard.style.display = 'block';
                    convertBtn.disabled = false;
                    window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' });
                }, 500);
            }
            if (progressFill) progressFill.style.width = `${progress}%`;
        }, 500);
    });

    // ----------------------------------------------------
    // ADVANCED HACKING EFFECTS (Video HUD & Telemetry)
    // ----------------------------------------------------
    const toggleHud = document.getElementById('toggle-hud');
    const videoHud = document.getElementById('video-hud');

    if (toggleHud && videoHud) {
        toggleHud.addEventListener('change', () => {
            if (toggleHud.checked) {
                videoHud.classList.add('active');
            } else {
                videoHud.classList.remove('active');
            }
        });
    }

    const telemetryLog = document.getElementById('telemetry-log');
    const blurBtn = document.querySelector('#view-video-telemetry .btn-format');

    if (blurBtn && telemetryLog) {
        blurBtn.addEventListener('click', () => {
            const vals = telemetryLog.querySelectorAll('.tel-val');
            vals.forEach(val => {
                val.textContent = '******';
                val.className = 'tel-val glitch';
                val.setAttribute('data-text', '******');
            });
            blurBtn.innerHTML = '<i data-lucide="check" size="14"></i> Métadonnées Purgées';
            blurBtn.style.color = 'var(--success)';
            blurBtn.style.borderColor = 'var(--success)';
            lucide.createIcons();
            setTimeout(() => {
                const vals = telemetryLog.querySelectorAll('.tel-val');
                vals.forEach(val => {
                    val.className = 'tel-val';
                });
            }, 2000);
        });
    }

    // ----------------------------------------------------
    // Deepfake timeline scanner (client-side simulation)
    // ----------------------------------------------------
    const scannerRoot = document.getElementById('deepfake-scanner');
    const scannerTrack = document.getElementById('scanner-track');
    const scannerSegmentsEl = document.getElementById('scanner-segments');
    const scannerPlayhead = document.getElementById('scanner-playhead');
    const scannerTimeHint = document.getElementById('scanner-time-hint');
    const scannerStatusLabel = document.getElementById('scanner-status-label');
    const scannerConfidence = document.getElementById('scanner-confidence');
    const scannerSegmentCountEl = document.getElementById('scanner-segment-count');
    const scannerSummary = document.getElementById('scanner-summary');
    const scannerZonesList = document.getElementById('scanner-zones-list');
    const scannerRunBtn = document.getElementById('scanner-run-btn');
    const scannerRunBtnLabel = document.getElementById('scanner-run-btn-label');

    let scannerSegmentCount = 0;
    let scannerAnalysisBusy = false;

    function hashStr(str) {
        let h = 2166136261;
        for (let i = 0; i < str.length; i++) {
            h ^= str.charCodeAt(i);
            h = Math.imul(h, 16777619);
        }
        return h >>> 0;
    }

    function mulberry32(seed) {
        return function () {
            let t = (seed += 0x6d2b79f5);
            t = Math.imul(t ^ (t >>> 15), t | 1);
            t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
            return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
        };
    }

    function formatScannerTime(sec) {
        if (!Number.isFinite(sec)) return '—';
        const m = Math.floor(sec / 60);
        const s = sec % 60;
        const pad = (n) => (n < 10 ? '0' : '') + n;
        return `${pad(m)}:${pad(Math.floor(s))}.${Math.floor((s % 1) * 100).toString().padStart(2, '0')}`;
    }

    function segmentCountForDuration(duration) {
        if (!Number.isFinite(duration) || duration <= 0) return 32;
        return Math.min(96, Math.max(24, Math.round(duration * 1.2)));
    }

    function buildSegmentElements(count, duration) {
        if (!scannerSegmentsEl) return;
        scannerSegmentsEl.innerHTML = '';
        scannerSegmentCount = count;
        const segDur = duration / count;
        for (let i = 0; i < count; i++) {
            const el = document.createElement('div');
            el.className = 'scanner-segment';
            el.dataset.index = String(i);
            const t0 = i * segDur;
            const t1 = (i + 1) * segDur;
            el.title = `${t0.toFixed(2)}s → ${t1.toFixed(2)}s`;
            scannerSegmentsEl.appendChild(el);
        }
    }

    function suspiciousMaskFromSeed(seed, length) {
        const rng = mulberry32(seed);
        const mask = new Array(length).fill(false);
        const numZones = 2 + Math.floor(rng() * 3);
        const maxSpan = Math.min(8, Math.max(3, Math.floor(length * 0.12)));
        for (let z = 0; z < numZones; z++) {
            const span = 1 + Math.floor(rng() * maxSpan);
            const startMax = Math.max(0, length - span);
            const start = Math.floor(rng() * (startMax + 1));
            for (let i = start; i < start + span && i < length; i++) mask[i] = true;
        }
        return mask;
    }

    function mergeSuspiciousRanges(mask, duration) {
        const n = mask.length;
        const segDur = duration / n;
        const ranges = [];
        let i = 0;
        while (i < n) {
            if (!mask[i]) {
                i++;
                continue;
            }
            let j = i;
            while (j < n && mask[j]) j++;
            ranges.push({
                start: i * segDur,
                end: j * segDur,
            });
            i = j;
        }
        return ranges;
    }

    function resetScannerUi() {
        if (scannerRoot) scannerRoot.classList.remove('is-scanned');
        if (scannerSegmentsEl) scannerSegmentsEl.innerHTML = '';
        scannerSegmentCount = 0;
        if (scannerPlayhead) {
            scannerPlayhead.classList.remove('is-visible');
            scannerPlayhead.style.left = '0%';
        }
        if (scannerTimeHint) scannerTimeHint.textContent = '—';
        if (scannerStatusLabel) {
            scannerStatusLabel.textContent = 'En attente';
            scannerStatusLabel.classList.remove('is-warn', 'is-ok');
        }
        if (scannerConfidence) {
            scannerConfidence.textContent = '—';
            scannerConfidence.classList.remove('is-warn', 'is-ok');
        }
        if (scannerSegmentCountEl) scannerSegmentCountEl.textContent = '—';
        if (scannerSummary) {
            scannerSummary.textContent = 'Importez une vidéo, puis lancez l’analyse pour cartographier la timeline.';
            scannerSummary.classList.remove('is-alert');
        }
        if (scannerZonesList) {
            scannerZonesList.innerHTML = '';
            scannerZonesList.hidden = true;
        }
        if (scannerRunBtn) scannerRunBtn.disabled = true;
        if (scannerTrack) scannerTrack.classList.remove('is-busy');
        scannerAnalysisBusy = false;
    }

    function syncScannerPlayhead() {
        const duration = videoPreview.duration;
        if (!scannerPlayhead || !Number.isFinite(duration) || duration <= 0) return;
        const t = videoPreview.currentTime;
        const pct = Math.min(100, Math.max(0, (t / duration) * 100));
        scannerPlayhead.style.left = `${pct}%`;
        scannerPlayhead.classList.add('is-visible');
        if (scannerTimeHint) {
            scannerTimeHint.textContent = `${formatScannerTime(t)} / ${formatScannerTime(duration)}`;
        }
        if (scannerTrack) {
            scannerTrack.setAttribute('aria-valuenow', String(Math.round(pct)));
        }
    }

    function initScannerForVideo(file) {
        resetScannerUi();
        if (!file || !scannerSegmentsEl) return;
        const onMeta = () => {
            const d = videoPreview.duration;
            if (!Number.isFinite(d) || d <= 0) return;
            const count = segmentCountForDuration(d);
            buildSegmentElements(count, d);
            if (scannerSegmentCountEl) scannerSegmentCountEl.textContent = String(count);
            if (scannerStatusLabel) {
                scannerStatusLabel.textContent = 'Prêt';
                scannerStatusLabel.classList.add('is-ok');
            }
            if (scannerSummary) {
                scannerSummary.textContent = 'Timeline prête. Lancez l’analyse IA pour détecter des incohérences temporelles (simulation locale).';
                scannerSummary.classList.remove('is-alert');
            }
            if (scannerRunBtn) scannerRunBtn.disabled = false;
            syncScannerPlayhead();
        };
        if (Number.isFinite(videoPreview.duration) && videoPreview.duration > 0) onMeta();
        else videoPreview.addEventListener('loadedmetadata', onMeta, { once: true });
    }

    function applyScanResults(mask, duration) {
        if (!scannerRoot || !scannerSegmentsEl) return;
        const children = scannerSegmentsEl.querySelectorAll('.scanner-segment');
        let suspiciousCount = 0;
        const segDur = duration / mask.length;
        children.forEach((el, i) => {
            el.classList.remove('clean', 'suspicious');
            const t0 = i * segDur;
            const t1 = (i + 1) * segDur;
            if (mask[i]) {
                el.classList.add('suspicious');
                suspiciousCount++;
                el.title = `${t0.toFixed(2)}s → ${t1.toFixed(2)}s — segment suspect`;
            } else {
                el.classList.add('clean');
                el.title = `${t0.toFixed(2)}s → ${t1.toFixed(2)}s — cohérent`;
            }
        });
        scannerRoot.classList.add('is-scanned');

        const ratio = suspiciousCount / mask.length;
        const confidence = Math.max(38, Math.min(97, Math.round(96 - ratio * 110 - (hashStr(String(ratio)) % 7))));

        if (scannerConfidence) {
            scannerConfidence.textContent = `${confidence}%`;
            scannerConfidence.classList.toggle('is-warn', confidence < 72);
            scannerConfidence.classList.toggle('is-ok', confidence >= 72);
        }
        if (scannerStatusLabel) {
            scannerStatusLabel.textContent = suspiciousCount ? 'Anomalies détectées' : 'Aucune anomalie';
            scannerStatusLabel.classList.toggle('is-warn', suspiciousCount > 0);
            scannerStatusLabel.classList.toggle('is-ok', suspiciousCount === 0);
        }

        const ranges = mergeSuspiciousRanges(mask, duration);
        if (scannerZonesList) {
            scannerZonesList.innerHTML = '';
            if (ranges.length) {
                scannerZonesList.hidden = false;
                ranges.forEach((r, idx) => {
                    const li = document.createElement('li');
                    li.textContent = `Plage ${idx + 1}: ${r.start.toFixed(2)}s — ${r.end.toFixed(2)}s (Δ ${(r.end - r.start).toFixed(2)}s)`;
                    scannerZonesList.appendChild(li);
                });
            } else scannerZonesList.hidden = true;
        }

        if (scannerSummary) {
            if (ranges.length) {
                scannerSummary.textContent = `[${ranges.length} plage(s) suspecte(s)] — Score confiance ${confidence}%. Revue manuelle recommandée sur les segments surlignés.`;
                scannerSummary.classList.add('is-alert');
            } else {
                scannerSummary.textContent = `Aucune incohérence majeure sur ${mask.length} segments (simulation). Score ${confidence}%.`;
                scannerSummary.classList.remove('is-alert');
            }
        }
    }

    function runScannerAnalysis() {
        if (scannerAnalysisBusy) return;
        if (!selectedFile || !scannerTrack || !scannerSegmentsEl) return;
        const duration = videoPreview.duration;
        if (!Number.isFinite(duration) || duration <= 0) {
            alert('Durée vidéo inconnue. Patientez le chargement.');
            return;
        }
        if (scannerSegmentCount === 0) {
            const count = segmentCountForDuration(duration);
            buildSegmentElements(count, duration);
            if (scannerSegmentCountEl) scannerSegmentCountEl.textContent = String(count);
        }

        const seed =
            hashStr(`${selectedFile.name}|${selectedFile.size}|${Math.floor(duration * 1000)}`) ^ 0x9e3779b9;
        scannerAnalysisBusy = true;
        scannerTrack.classList.add('is-busy');
        if (scannerRunBtn) scannerRunBtn.disabled = true;
        if (scannerRunBtnLabel) scannerRunBtnLabel.textContent = 'Analyse en cours…';
        if (scannerStatusLabel) {
            scannerStatusLabel.textContent = 'Analyse…';
            scannerStatusLabel.classList.remove('is-ok', 'is-warn');
        }

        const steps = ['Échantillonnage temporel…', 'Cartographie des artefacts…', 'Synthèse heuristique…'];
        let step = 0;
        const stepIv = setInterval(() => {
            step = (step + 1) % steps.length;
            if (scannerStatusLabel) scannerStatusLabel.textContent = steps[step];
        }, 420);

        const analysisDelayMs = 1600 + (hashStr(`delay|${seed}`) % 550);
        window.setTimeout(() => {
            clearInterval(stepIv);
            const mask = suspiciousMaskFromSeed(seed, scannerSegmentCount);
            if (scannerRoot) scannerRoot.classList.remove('is-scanned');
            applyScanResults(mask, duration);
            scannerTrack.classList.remove('is-busy');
            if (scannerRunBtn) scannerRunBtn.disabled = false;
            if (scannerRunBtnLabel) scannerRunBtnLabel.textContent = 'Relancer l’analyse';
            scannerAnalysisBusy = false;
            syncScannerPlayhead();
        }, analysisDelayMs);
    }

    if (scannerTrack) {
        scannerTrack.addEventListener('click', (e) => {
            const duration = videoPreview.duration;
            if (!Number.isFinite(duration) || duration <= 0) return;
            const rect = scannerTrack.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const ratio = Math.min(1, Math.max(0, x / rect.width));
            videoPreview.currentTime = ratio * duration;
            syncScannerPlayhead();
        });

        scannerTrack.addEventListener('keydown', (e) => {
            const duration = videoPreview.duration;
            if (!Number.isFinite(duration) || duration <= 0) return;
            const step = Math.min(1, duration * 0.02);
            if (e.key === 'ArrowLeft') {
                e.preventDefault();
                videoPreview.currentTime = Math.max(0, videoPreview.currentTime - step);
            } else if (e.key === 'ArrowRight') {
                e.preventDefault();
                videoPreview.currentTime = Math.min(duration, videoPreview.currentTime + step);
            } else return;
            syncScannerPlayhead();
        });
    }

    if (scannerRunBtn) {
        scannerRunBtn.addEventListener('click', () => runScannerAnalysis());
    }

    videoPreview.addEventListener('seeked', syncScannerPlayhead);

    resetScannerUi();

});
