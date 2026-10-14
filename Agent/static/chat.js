const chatInput = document.querySelector("#chat-input");
const sendButton = document.querySelector("#send-btn");
const chatContainer = document.querySelector(".chat-container");
const themeButton = document.querySelector("#theme-btn");
const deleteButton = document.querySelector("#delete-btn");
const initialInputHeight = chatInput.scrollHeight;
let activeStream = null;

function loadHistory() {
    try {
        const history = JSON.parse(localStorage.getItem("history") || "[]");
        return Array.isArray(history) ? history.filter(item =>
            item && typeof item.question === "string" && typeof item.response === "string"
        ).slice(-5).map(item => ({ question: item.question.slice(0, 2000), response: item.response.slice(0, 6000) })) : [];
    } catch {
        return [];
    }
}

function appendMessage(text, kind) {
    const chat = document.createElement("div");
    chat.className = `chat ${kind}`;
    // Only this fixed template is HTML. User and model content use textContent.
    chat.innerHTML = `<div class="chat-content"><div class="chat-details"><img alt="avatar"><p></p></div></div>`;
    chat.querySelector("img").src = kind === "outgoing" ? "static/images/user.jpg" : "static/images/chatbot.jpg";
    const paragraph = chat.querySelector("p");
    paragraph.textContent = text;
    paragraph.style.whiteSpace = "pre-wrap";
    chatContainer.appendChild(chat);
    chatContainer.scrollTo(0, chatContainer.scrollHeight);
    return paragraph;
}

function loadChats() {
    chatContainer.replaceChildren();
    const history = loadHistory();
    if (!history.length) {
        const intro = document.createElement("div");
        intro.className = "default-text";
        intro.innerHTML = "<h1>전북대 AI 멘토</h1><p>궁금한 것을 물어보세요.</p>";
        chatContainer.appendChild(intro);
    }
    for (const item of history) {
        appendMessage(item.question, "outgoing");
        appendMessage(item.response, "incoming");
    }
    // Retire the old HTML-based cache.
    localStorage.removeItem("all-chats");
}

function setBusy(busy) {
    chatInput.disabled = busy;
    sendButton.disabled = busy;
    sendButton.setAttribute("aria-disabled", String(busy));
}

function getChatResponse(question, paragraph) {
    const history = loadHistory();
    while (JSON.stringify(history).length > 15000) history.shift();
    const query = new URLSearchParams({ question, history: JSON.stringify(history) });
    const stream = new EventSource(`/get-curriculum?${query}`);
    activeStream = stream;
    let responseText = "";
    let courses = [];
    let finished = false;

    function finish(save) {
        if (finished) return;
        finished = true;
        stream.close();
        activeStream = null;
        setBusy(false);
        if (save) {
            history.push({ question, response: responseText });
            localStorage.setItem("history", JSON.stringify(history.slice(-5)));
            if (courses.length) populateCourseButtons(courses);
        }
        chatInput.focus();
    }

    stream.onopen = () => { paragraph.textContent = ""; };
    stream.addEventListener("text", event => {
        const chunk = JSON.parse(event.data);
        if (typeof chunk !== "string") return;
        responseText += chunk;
        paragraph.textContent = responseText;
        chatContainer.scrollTo(0, chatContainer.scrollHeight);
    });
    stream.addEventListener("courses", event => {
        const batch = JSON.parse(event.data);
        if (Array.isArray(batch)) courses.push(...batch);
    });
    stream.addEventListener("status", () => {});
    stream.addEventListener("done", () => finish(true));
    stream.onerror = event => {
        let message = "서버 연결이 끊겼습니다. 서버 설정과 실행 상태를 확인해 주세요.";
        if (typeof event.data === "string") {
            try { message = JSON.parse(event.data).message || message; } catch { /* transport error */ }
        }
        paragraph.textContent = responseText ? `${responseText}\n\n${message}` : message;
        finish(false);
    };
}

function handleOutgoingChat() {
    if (activeStream) return;
    const question = chatInput.value.trim();
    if (!question) return;
    if (question.length > 2000) {
        alert("질문은 2,000자 이하로 입력해 주세요.");
        return;
    }
    chatInput.value = "";
    chatInput.style.height = `${initialInputHeight}px`;
    chatContainer.querySelector(".default-text")?.remove();
    appendMessage(question, "outgoing");
    const paragraph = appendMessage("연결 중…", "incoming");
    setBusy(true);
    getChatResponse(question, paragraph);
}

function populateCourseButtons(courses) {
    const table = document.getElementById("curriculum-table");
    for (let i = 1; i <= 30; i++) {
        const button = document.getElementById(`btn${i}`);
        button.textContent = "";
        button.onclick = null;
    }
    const semesters = [[4, "2학기"], [4, "1학기"], [3, "2학기"], [3, "1학기"], [2, "2학기"], [2, "1학기"]];
    semesters.forEach(([year, semester], group) => {
        courses.filter(course => course && Number(course["학년"]) === year && course["학기"] === semester)
            .slice(0, 5).forEach((course, index) => {
                const button = document.getElementById(`btn${group * 5 + index + 1}`);
                button.textContent = `${course["교과목명"] || ""}\n${course["학과"] || ""}`;
                button.style.whiteSpace = "pre-wrap";
                button.onclick = () => displayCourseInfo(course);
            });
    });
    table.style.display = "table";
    document.getElementById("curriculum-prompts-btn").style.display = "block";
}

function displayCourseInfo(course) {
    document.getElementById("course-name").textContent = course["교과목명"] || "";
    document.getElementById("course-department").textContent = `학과: ${course["학과"] || ""}`;
    const goal = document.getElementById("course-goal");
    goal.textContent = `수업목표: ${course["수업목표"] || ""}`;
    goal.style.whiteSpace = "pre-wrap";
    document.getElementById("course-info").style.display = "block";
    document.getElementById("explain-prompts-btn").style.display = "block";
}

deleteButton.addEventListener("click", () => {
    if (activeStream) return;
    if (confirm("저장된 대화 기록을 삭제할까요?")) {
        localStorage.removeItem("history");
        loadChats();
        document.getElementById("curriculum-table").style.display = "none";
        document.getElementById("course-info").style.display = "none";
        document.getElementById("curriculum-prompts-btn").style.display = "none";
        document.getElementById("explain-prompts-btn").style.display = "none";
    }
});
themeButton.addEventListener("click", () => {
    const light = document.body.classList.toggle("light-mode");
    localStorage.setItem("themeColor", light ? "light_mode" : "dark_mode");
    themeButton.textContent = light ? "어둡게" : "밝게";
});
chatInput.addEventListener("input", () => {
    chatInput.style.height = `${initialInputHeight}px`;
    chatInput.style.height = `${chatInput.scrollHeight}px`;
});
chatInput.addEventListener("keydown", event => {
    if (event.key === "Enter" && !event.shiftKey && window.innerWidth > 800) {
        event.preventDefault();
        handleOutgoingChat();
    }
});
document.body.classList.toggle("light-mode", localStorage.getItem("themeColor") === "light_mode");
themeButton.textContent = document.body.classList.contains("light-mode") ? "어둡게" : "밝게";
loadChats();
sendButton.addEventListener("click", handleOutgoingChat);
window.addEventListener("beforeunload", () => activeStream?.close());
