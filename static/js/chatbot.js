/**
 * FinLab - Floating Conversational AI Chatbot
 */

document.addEventListener('DOMContentLoaded', () => {
    initChatbot();
});

function initChatbot() {
    const triggerBtn = document.getElementById('chatbot-trigger');
    const chatWindow = document.getElementById('chat-window');
    const closeBtn = document.getElementById('chat-close-btn');
    const inputField = document.getElementById('chat-user-input');
    const sendBtn = document.getElementById('chat-send-btn');
    const messagesContainer = document.getElementById('chat-messages');
    const suggestionChips = document.querySelectorAll('.chip-btn');
    const chatbotBadge = document.getElementById('chatbot-badge');

    if (!triggerBtn || !chatWindow) return;

    // Toggle Chat Window
    triggerBtn.addEventListener('click', () => {
        chatWindow.classList.toggle('open');
        if (chatWindow.classList.contains('open')) {
            if (chatbotBadge) chatbotBadge.style.display = 'none';
            if (inputField) inputField.focus();
            scrollToBottom();
        }
    });

    if (closeBtn) {
        closeBtn.addEventListener('click', () => {
            chatWindow.classList.remove('open');
        });
    }

    // Handle Suggestions
    suggestionChips.forEach(chip => {
        chip.addEventListener('click', () => {
            const question = chip.getAttribute('data-question') || chip.textContent.trim();
            sendMessage(question);
        });
    });

    // Send on button click
    if (sendBtn) {
        sendBtn.addEventListener('click', () => {
            const text = inputField.value.trim();
            if (text) {
                sendMessage(text);
                inputField.value = '';
            }
        });
    }

    // Send on Enter
    if (inputField) {
        inputField.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                const text = inputField.value.trim();
                if (text) {
                    sendMessage(text);
                    inputField.value = '';
                }
            }
        });
    }

    // Main send message function
    async function sendMessage(text) {
        // Append user bubble
        appendMessage('user', text);
        scrollToBottom();

        // Show typing indicator
        const typingId = appendTypingIndicator();
        scrollToBottom();

        try {
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: text })
            });

            const data = await response.json();
            removeTypingIndicator(typingId);

            if (data.reply) {
                appendMessage('bot', data.reply);
            } else {
                appendMessage('bot', 'Xin lỗi, tôi chưa hiểu rõ câu hỏi. Bạn có thể thử lại các câu hỏi gợi ý bên dưới!');
            }
        } catch (err) {
            console.error('Chatbot error:', err);
            removeTypingIndicator(typingId);
            appendMessage('bot', 'Đã xảy ra lỗi khi kết nối với máy chủ AI.');
        }

        scrollToBottom();
    }

    function appendMessage(sender, text) {
        const bubble = document.createElement('div');
        bubble.classList.add('msg-bubble');
        bubble.classList.add(sender === 'user' ? 'msg-user' : 'msg-bot');

        // Simple Markdown parser for bold and linebreaks
        const formatted = formatMarkdown(text);
        bubble.innerHTML = formatted;

        messagesContainer.appendChild(bubble);
    }

    function appendTypingIndicator() {
        const id = 'typing-' + Date.now();
        const indicator = document.createElement('div');
        indicator.id = id;
        indicator.classList.add('msg-bubble', 'msg-bot');
        indicator.style.display = 'flex';
        indicator.style.gap = '4px';
        indicator.style.alignItems = 'center';
        indicator.style.padding = '0.6rem 0.9rem';
        indicator.innerHTML = `
            <span style="width: 6px; height: 6px; background: #94a3b8; border-radius: 50%; animation: bounce 1.2s infinite 0.1s;"></span>
            <span style="width: 6px; height: 6px; background: #94a3b8; border-radius: 50%; animation: bounce 1.2s infinite 0.2s;"></span>
            <span style="width: 6px; height: 6px; background: #94a3b8; border-radius: 50%; animation: bounce 1.2s infinite 0.3s;"></span>
        `;
        messagesContainer.appendChild(indicator);
        return id;
    }

    function removeTypingIndicator(id) {
        const el = document.getElementById(id);
        if (el) el.remove();
    }

    function scrollToBottom() {
        setTimeout(() => {
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
        }, 50);
    }

    function formatMarkdown(text) {
        if (!text) return '';
        let escaped = text
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;');

        // Bold **text**
        escaped = escaped.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        // Italic *text*
        escaped = escaped.replace(/\*(.*?)\*/g, '<em>$1</em>');
        // Newlines to <br>
        escaped = escaped.replace(/\n/g, '<br>');

        return escaped;
    }
}
