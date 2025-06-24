// Update the Drive connection button and status
function updateDriveStatus(connected) {
    const btn = document.getElementById('connect-drive-btn');
    const status = document.getElementById('drive-status');
    if (connected) {
        btn.textContent = 'Logout from Drive';
        status.innerHTML = '<span title="Google Drive connected" style="color:#25be5b;font-size:1.1em;">&#9679; Connected</span>';
    } else {
        btn.textContent = 'Connect to Google Drive';
        status.innerHTML = '';
    }
}

// Loads and displays previous meeting transcripts
async function loadTranscripts() {
    const transcriptList = document.querySelector('.transcript-list');
    transcriptList.innerHTML = '<div style="padding: 1.5em; color: #9eacc2; text-align: center;">Loading...</div>';
    try {
        const res = await fetch('/drive/meet-transcripts');
        const data = await res.json();

        if (data.error === "not_connected") {
            transcriptList.innerHTML = `<div style="padding:1.2em;color:#999;text-align:center;">
                Connect Drive to get recent transcripts
            </div>`;
            return;
        }
        if (data.error === "no_folder" || data.error === "no_transcripts") {
            transcriptList.innerHTML = `<div style="padding:1.2em;color:#999;text-align:center;">
                No transcripts available,<br>save the transcripts in <b>Meet Recordings</b> folder
            </div>`;
            return;
        }

        transcriptList.innerHTML = '';
        data.transcripts.forEach(t => {
            const item = document.createElement('div');
            item.className = 'transcript-item';

            // File name (truncate if long)
            const nameSpan = document.createElement('span');
            nameSpan.textContent = t.name.length > 32 ? t.name.slice(0,32) + '…' : t.name;

            // Copy button
            const copyBtn = document.createElement('button');
            copyBtn.innerHTML = `<svg height="18" width="18" viewBox="0 0 24 24" style="vertical-align:middle;"><path d="M16 1H4a2 2 0 0 0-2 2v14h2V3h12V1zm3 4H8a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h11a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2zm0 18H8V7h11v16z" fill="#6e7dab"/></svg>`;
            copyBtn.className = 'copy-btn';
            copyBtn.title = "Copy file name";

            copyBtn.onclick = () => {
                navigator.clipboard.writeText(t.name);
                copyBtn.innerHTML = '✓'; // feedback
                setTimeout(() => {
                    copyBtn.innerHTML = `<svg height="18" width="18" viewBox="0 0 24 24" style="vertical-align:middle;"><path d="M16 1H4a2 2 0 0 0-2 2v14h2V3h12V1zm3 4H8a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h11a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2zm0 18H8V7h11v16z" fill="#6e7dab"/></svg>`;
                }, 1200);
            };

            item.appendChild(nameSpan);
            item.appendChild(copyBtn);
            transcriptList.appendChild(item);
        });
    } catch (e) {
        transcriptList.innerHTML = `<div style="padding:1.2em;color:#999;text-align:center;">Failed to load transcripts.</div>`;
    }
}

// Initial Drive status check and handler for connect/logout
function checkAndSetDriveStatus() {
    fetch('/auth/status')
        .then(res => res.json())
        .then(data => {
            updateDriveStatus(data.connected);
        });
}

document.getElementById('connect-drive-btn').onclick = function() {
    if (this.textContent.includes('Logout')) {
        // Logout
        fetch('/auth/logout').then(() => {
            updateDriveStatus(false);
            loadTranscripts();   // Refresh transcript panel on logout
        });
    } else {
        // Connect (redirect for OAuth)
        window.location.href = '/auth';
    }
};

document.getElementById('refresh-transcripts-btn').onclick = loadTranscripts;

window.addEventListener('DOMContentLoaded', () => {
    checkAndSetDriveStatus();
    loadTranscripts();
});

// Placeholder logic for transcript display and action buttons
document.getElementById('fetch-transcript-btn').onclick = function() {
    const meetingId = document.getElementById('meeting-id-input').value;
    document.getElementById('transcript-display').innerHTML =
        `<p class="placeholder">[Would fetch transcript for Meeting ID: ${meetingId}]</p>`;
};

document.getElementById('create-action-item-btn').onclick = function() {
    alert('Create Action Item (not implemented yet)');
};

document.getElementById('add-extra-context-btn').onclick = function() {
    alert('Add Extra Context (not implemented yet)');
};
