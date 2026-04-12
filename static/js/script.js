document.addEventListener('DOMContentLoaded', () => {
    const dropZone = document.getElementById('drop-zone');
    const fileInput = document.getElementById('file-input');
    const uploadPrompt = document.getElementById('upload-prompt');
    const previewContainer = document.getElementById('preview-container');
    const previewImg = document.getElementById('preview-img');
    const removeBtn = document.getElementById('remove-img');
    const convertBtn = document.getElementById('convert-btn');

    // UI Feedback elements
    const resultCard = document.getElementById('result-card');

    let selectedFile = null;

    // Range Sliders (Quality, Brightness, etc.)
    const rangeSliders = document.querySelectorAll('.range-slider');
    rangeSliders.forEach(slider => {
        const valueDisplay = slider.parentElement.querySelector('.value');
        slider.addEventListener('input', () => {
            let unit = slider.max == 100 && slider.min == 0 ? '%' : '';
            if (valueDisplay) valueDisplay.textContent = slider.value + unit;

            // Special case for segments if it's the quality slider
            if (slider.parentElement.parentElement.querySelector('.progress-segments')) {
                updateSegments(slider.value);
            }
        });
    });

    function updateSegments(value) {
        const segments = document.querySelectorAll('.segment');
        const activeCount = Math.floor((value / 100) * segments.length);
        segments.forEach((seg, i) => {
            if (i < activeCount) seg.classList.add('active');
            else seg.classList.remove('active');
        });
    }

    // Format Selection Logic
    const formatButtons = document.querySelectorAll('.btn-format');
    formatButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            const card = btn.closest('.format-selection-card');
            if (!card) return;
            card.querySelectorAll('.btn-format').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
        });
    });

    // Ratio Buttons Logic
    const ratioButtons = document.querySelectorAll('.btn-ratio');
    ratioButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            btn.parentElement.querySelectorAll('.btn-ratio').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
        });
    });

    // Filter Items
    const filterItems = document.querySelectorAll('.filter-item');
    filterItems.forEach(item => {
        item.addEventListener('click', () => {
            filterItems.forEach(i => i.classList.remove('active'));
            item.classList.add('active');

            // Preview effect (simple CSS filter mock)
            const filterType = item.querySelector('.filter-thumb').classList[1];
            applyFilterToPreview(filterType);
        });
    });

    function applyFilterToPreview(type) {
        const filters = {
            'original': '',
            'grayscale': 'grayscale(1)',
            'sepia': 'sepia(1)',
            'vivid': 'saturate(2)',
            'cool': 'hue-rotate(180deg)',
            'warm': 'sepia(0.3) saturate(1.2) hue-rotate(-10deg)'
        };
        previewImg.style.filter = filters[type] || '';
    }

    // Upload interactions
    dropZone.addEventListener('click', (e) => {
        if (!selectedFile && !e.target.closest('.btn-remove')) fileInput.click();
    });

    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) handleFile(e.target.files[0]);
    });

    function handleFile(file) {
        if (!file.type.startsWith('image/')) return alert('Fichier invalide');
        selectedFile = file;
        const reader = new FileReader();
        reader.onload = (e) => {
            previewImg.src = e.target.result;
            uploadPrompt.style.display = 'none';
            previewContainer.style.display = 'flex';
            dropZone.style.borderStyle = 'solid';
        };
        reader.readAsDataURL(file);
    }

    removeBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        selectedFile = null;
        fileInput.value = '';
        uploadPrompt.style.display = 'block';
        previewContainer.style.display = 'none';
        dropZone.style.borderStyle = 'dashed';
        if (resultCard) resultCard.style.display = 'none';
    });

    // Pipeline View Switching
    const pills = document.querySelectorAll('.pipeline-pills .pill');
    const views = document.querySelectorAll('.pipeline-view');

    function randomizeInjectionHex() {
        const chars = '0123456789ABCDEF';
        document.querySelectorAll('#view-injection .hex-bytes').forEach((span) => {
            if (span.querySelector('.hex-highlight')) return;
            let newHex = '';
            for (let i = 0; i < 8; i++) {
                newHex += chars[Math.floor(Math.random() * 16)];
                newHex += chars[Math.floor(Math.random() * 16)];
                if (i < 7) newHex += ' ';
            }
            span.textContent = newHex;
        });
    }

    pills.forEach(pill => {
        pill.addEventListener('click', () => {
            const targetView = pill.getAttribute('data-view');

            // Update pills
            pills.forEach(p => p.classList.remove('active'));
            pill.classList.add('active');

            // Update views
            views.forEach(v => {
                v.classList.remove('active');
                if (v.id === `view-${targetView}`) v.classList.add('active');
            });

            // Update preview overlay (only show for recadrage)
            const cropOverlay = document.querySelector('.crop-overlay');
            if (cropOverlay) {
                cropOverlay.style.display = targetView === 'recadrage' ? 'block' : 'none';
            }

            if (targetView === 'injection') {
                randomizeInjectionHex();
            }
        });
    });

    // Forensics Mock Logic
    const verifyBtn = document.getElementById('btn-verify-fingerprint');
    if (verifyBtn) {
        verifyBtn.addEventListener('click', () => {
            verifyBtn.disabled = true;
            verifyBtn.textContent = 'Vérification...';
            setTimeout(() => {
                verifyBtn.disabled = false;
                verifyBtn.textContent = 'Correspondance OK';
                verifyBtn.style.color = 'var(--success)';
                verifyBtn.style.borderColor = 'var(--success)';
            }, 1000);
        });
    }

    const lsbToggle = document.getElementById('lsb-scan-toggle');
    const statusBadge = document.getElementById('lsb-status-badge');
    if (lsbToggle && statusBadge) {
        lsbToggle.addEventListener('change', () => {
            if (lsbToggle.checked) {
                statusBadge.textContent = 'Scan en cours...';
                statusBadge.classList.remove('muted');
                statusBadge.style.color = '';
                setTimeout(() => {
                    statusBadge.textContent = 'Aucune anomalie détectée';
                    statusBadge.style.color = 'var(--success)';
                }, 1500);
            } else {
                statusBadge.textContent = 'Aucun scan actif';
                statusBadge.style.color = '';
                statusBadge.classList.add('muted');
            }
        });
    }

    // Original convert-btn logic
    convertBtn.addEventListener('click', () => {
        if (!selectedFile) return alert('Importez une image');

        convertBtn.disabled = true;
        const originalText = convertBtn.innerHTML;
        convertBtn.innerHTML = 'Traitement en cours...';

        setTimeout(() => {
            if (resultCard) resultCard.style.display = 'block';
            convertBtn.disabled = false;
            convertBtn.innerHTML = originalText;
            lucide.createIcons();
            window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' });
        }, 2000);
    });

    // ----------------------------------------------------
    // ADVANCED HACKING EFFECTS (Console & Hex Editor)
    // ----------------------------------------------------

    const btnHack = document.getElementById('btn-run-hack');
    const terminalOutput = document.getElementById('terminal-output');
    const hackerTerminal = document.getElementById('hacker-terminal');

    function scrollTerminalToBottom() {
        const el = hackerTerminal || terminalOutput?.parentElement;
        if (el) el.scrollTop = el.scrollHeight;
    }

    if (btnHack && terminalOutput) {
        const fakeCommands = [
            "> nmap -p- --min-rate=1000 target.sys",
            "[SYSTEM] Port 22 OPEN ... Brute forcing SSH...",
            "> hashcat -m 0 hash.txt wordlist.txt",
            "[SYSTEM] Hash cracked: *********",
            "> python3 extract_lsb.py --target image.png --channel B",
            "[!] EXTRACTING HIDDEN PAYLOAD...",
            "01010011 01000101 01000011 01010010 01000101 01010100",
            "[SUCCESS] Payload decrypted and loaded."
        ];

        btnHack.addEventListener('click', () => {
            btnHack.disabled = true;
            btnHack.innerHTML = '<i data-lucide="loader" class="spin"></i> Attaque en cours...';
            lucide.createIcons();

            let cmdIndex = 0;
            const currentInputLine = document.querySelector('.current-input');
            if(currentInputLine) currentInputLine.remove();

            function typeCommand() {
                if (cmdIndex >= fakeCommands.length) {
                    btnHack.disabled = false;
                    btnHack.innerHTML = '<i data-lucide="terminal-square"></i> Lancer l\'attaque';
                    lucide.createIcons();
                    // Put cursor back
                    const cursorLine = document.createElement('div');
                    cursorLine.className = 'terminal-line current-input';
                    cursorLine.innerHTML = '<span class="cursor-blink"></span>';
                    terminalOutput.appendChild(cursorLine);
                    scrollTerminalToBottom();
                    return;
                }

                const newLine = document.createElement('div');
                newLine.className = fakeCommands[cmdIndex].startsWith('>') ? 'terminal-line' : 'terminal-line warning';
                if(fakeCommands[cmdIndex].startsWith('[SUCCESS]')) newLine.className = 'terminal-line system';
                
                terminalOutput.appendChild(newLine);
                
                let charIndex = 0;
                let text = fakeCommands[cmdIndex];
                
                function typeChar() {
                    if (charIndex < text.length) {
                        newLine.textContent += text.charAt(charIndex);
                        charIndex++;
                        scrollTerminalToBottom();
                        setTimeout(typeChar, Math.random() * 30 + 10);
                    } else {
                        cmdIndex++;
                        setTimeout(typeCommand, 300);
                    }
                }
                typeChar();
            }

            typeCommand();
        });
    }

});
