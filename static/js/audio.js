document.addEventListener('DOMContentLoaded', () => {
    const dropZone = document.getElementById('drop-zone-audio');
    const audioInput = document.getElementById('audio-input');
    const uploadPrompt = document.getElementById('upload-prompt');
    const previewContainer = document.getElementById('audio-preview-container');
    const filenameDisplay = document.getElementById('audio-filename');
    const removeBtn = document.getElementById('remove-audio');
    const convertBtn = document.getElementById('convert-audio-btn');
    const choiceButtons = document.querySelectorAll('.btn-format');

    const pipelinePills = document.querySelectorAll('.pill');
    const pipelineViews = document.querySelectorAll('.pipeline-view');

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

    // Player
    const playPauseBtn = document.getElementById('play-pause');
    const stopBtn = document.getElementById('stop-audio');
    const playIcon = document.getElementById('play-icon');
    const trimStart = document.getElementById('trim-start');
    const trimEnd = document.getElementById('trim-end');

    // UI Feedback
    const progressContainer = document.getElementById('progress-container');
    const progressFill = document.getElementById('progress-fill');
    const resultCard = document.getElementById('result-card');
    const transcriptionArea = document.getElementById('transcription-area');
    const transcriptionText = document.getElementById('transcription-text');
    const sttToggle = document.getElementById('stt-toggle');

    let selectedFile = null;
    let wavesurfer = null;

    const initWaveSurfer = () => {
        if (wavesurfer) wavesurfer.destroy();
        wavesurfer = WaveSurfer.create({
            container: '#waveform',
            waveColor: '#27272a',
            progressColor: '#3b82f6',
            cursorColor: '#3b82f6',
            barWidth: 2,
            barRadius: 3,
            height: 120,
        });

        wavesurfer.on('play', () => { playIcon.setAttribute('data-lucide', 'pause'); lucide.createIcons(); });
        wavesurfer.on('pause', () => { playIcon.setAttribute('data-lucide', 'play'); lucide.createIcons(); });
        wavesurfer.on('ready', () => { trimStart.value = 0; trimEnd.value = wavesurfer.getDuration().toFixed(1); });
    };

    // Format Choices
    const formatButtonsNew = document.querySelectorAll('.btn-format');
    formatButtonsNew.forEach(btn => {
        btn.addEventListener('click', () => {
            btn.closest('.format-selection-card').querySelectorAll('.btn-format').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
        });
    });

    // Upload
    dropZone.addEventListener('click', (e) => { if (!selectedFile) audioInput.click(); });
    audioInput.addEventListener('change', (e) => { if (e.target.files.length > 0) handleFile(e.target.files[0]); });

    function handleFile(file) {
        if (!file.type.startsWith('audio/')) return alert('Audio invalide');
        selectedFile = file;
        uploadPrompt.style.display = 'none';
        previewContainer.style.display = 'block';
        initWaveSurfer();
        wavesurfer.load(URL.createObjectURL(file));
    }

    playPauseBtn.addEventListener('click', (e) => { e.stopPropagation(); wavesurfer.playPause(); });
    stopBtn.addEventListener('click', (e) => { e.stopPropagation(); wavesurfer.stop(); });

    removeBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        if (wavesurfer) wavesurfer.stop();
        selectedFile = null;
        uploadPrompt.style.display = 'flex';
        previewContainer.style.display = 'none';
        resultCard.style.display = 'none';
        transcriptionArea.style.display = 'none';
    });

    // Action: AI Process
    convertBtn.addEventListener('click', () => {
        if (!selectedFile) return alert('Importez un audio');

        resultCard.style.display = 'none';
        transcriptionArea.style.display = 'none';
        progressContainer.style.display = 'block';
        progressFill.style.width = '0%';
        convertBtn.disabled = true;

        let progress = 0;
        const interval = setInterval(() => {
            progress += Math.random() * 20;
            if (progress >= 100) {
                progress = 100;
                clearInterval(interval);

                setTimeout(() => {
                    progressContainer.style.display = 'none';
                    resultCard.style.display = 'block';

                    if (sttToggle.checked) {
                        transcriptionArea.style.display = 'block';
                        transcriptionText.value = "Ceci est une simulation de transcription IA...\n\nL'audio analysé semble contenir une voix masculine parlant de technologie et de design minimaliste. La qualité sonore est excellente.";
                    }

                    convertBtn.disabled = false;
                    window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' });
                }, 500);
            }
            progressFill.style.width = `${progress}%`;
        }, 400);
    });
});
