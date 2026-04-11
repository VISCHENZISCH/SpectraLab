document.addEventListener('DOMContentLoaded', () => {
    const dropZone = document.getElementById('drop-zone-video');
    const videoInput = document.getElementById('video-input');
    const uploadPrompt = document.getElementById('upload-prompt');
    const previewContainer = document.getElementById('video-preview-container');
    const videoPreview = document.getElementById('video-preview');
    const removeBtn = document.getElementById('remove-video');
    const convertBtn = document.getElementById('convert-video-btn');
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

    // UI Feedback
    const progressContainer = document.getElementById('progress-container');
    const progressFill = document.getElementById('progress-fill');
    const resultCard = document.getElementById('result-card');

    let selectedFile = null;

    const formatButtonsNew = document.querySelectorAll('.btn-format');
    formatButtonsNew.forEach(btn => {
        btn.addEventListener('click', () => {
            btn.closest('.format-selection-card').querySelectorAll('.btn-format').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
        });
    });

    dropZone.addEventListener('click', () => { if (!selectedFile) videoInput.click(); });
    videoInput.addEventListener('change', (e) => { if (e.target.files.length > 0) handleFile(e.target.files[0]); });

    function handleFile(file) {
        if (!file.type.startsWith('video/')) return alert('Vidéo invalide');
        selectedFile = file;
        uploadPrompt.style.display = 'none';
        previewContainer.style.display = 'block';
        videoPreview.src = URL.createObjectURL(file);
        videoPreview.onloadedmetadata = () => {
            document.getElementById('trim-start-sidebar').value = 0;
            document.getElementById('trim-end-sidebar').value = Math.floor(videoPreview.duration);
            document.getElementById('total-time').textContent = formatTime(videoPreview.duration);
        };
    }

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
        selectedFile = null;
        videoPreview.src = '';
        uploadPrompt.style.display = 'flex';
        previewContainer.style.display = 'none';
        resultCard.style.display = 'none';
    });

    // Action: Video Rendering
    convertBtn.addEventListener('click', () => {
        if (!selectedFile) return alert('Importez une vidéo');

        resultCard.style.display = 'none';
        progressContainer.style.display = 'block';
        progressFill.style.width = '0%';
        convertBtn.disabled = true;

        let progress = 0;
        const interval = setInterval(() => {
            progress += Math.random() * 15; // Un peu plus lent car encodage vidéo
            if (progress >= 100) {
                progress = 100;
                clearInterval(interval);

                setTimeout(() => {
                    progressContainer.style.display = 'none';
                    resultCard.style.display = 'block';
                    convertBtn.disabled = false;
                    window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' });
                }, 500);
            }
            progressFill.style.width = `${progress}%`;
        }, 500);
    });
});
