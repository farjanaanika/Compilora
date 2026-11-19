
const languageSelect = document.getElementById("language");
const codeEditor = document.getElementById("code");
const terminal = document.getElementById("terminal");
const runButton = document.getElementById("runButton");

let currentProcessId = null;
let polling = false;
let inputBuffer = "";

const starterCode = {
    c: `#include <stdio.h>

int main() {
    printf("Hello from C!\\n");
    return 0;
}`,
    cpp: `#include <iostream>
using namespace std;

int main() {
    cout << "Hello from C++!" << endl;
    return 0;
}`,
    java: `public class Main {
    public static void main(String[] args) {
        System.out.println("Hello from Java!");
    }
}`
};

languageSelect.addEventListener("change", () => {
    codeEditor.value = starterCode[languageSelect.value];
    terminal.textContent = "Ready to compile and run.";
    currentProcessId = null;
    polling = false;
    inputBuffer = "";
});

async function checkBackend() {
    try {
        const response = await fetch("/api/health");
        const result = await response.json();
        terminal.textContent = result.message;
    } catch {
        terminal.textContent = "Cannot connect to backend.";
    }
}

async function sendTerminalInput(value) {
    if (!currentProcessId) {
        return;
    }

    try {
        const response = await fetch("/api/input", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                process_id: currentProcessId,
                input: value
            })
        });

        const result = await response.json();

        if (!response.ok) {
            terminal.textContent += "\n" + (result.error || "Input failed.");
        }
    } catch (error) {
        terminal.textContent += "\nInput error: " + error.message;
    }
}

terminal.addEventListener("keydown", async (event) => {
    if (!currentProcessId || !polling) {
        return;
    }

    if (event.key === "Enter") {
        event.preventDefault();

        terminal.textContent += "\n";

        const value = inputBuffer;
        inputBuffer = "";

        await sendTerminalInput(value);

        return;
    }

    if (event.key === "Backspace") {
        event.preventDefault();

        if (inputBuffer.length > 0) {
            inputBuffer = inputBuffer.slice(0, -1);
            terminal.textContent = terminal.textContent.slice(0, -1);
        }

        return;
    }

    if (event.key.length === 1 && !event.ctrlKey && !event.altKey) {
        event.preventDefault();

        inputBuffer += event.key;
        terminal.textContent += event.key;
    }
});

async function pollOutput() {
    if (!currentProcessId || !polling) {
        return;
    }

    try {
        const response = await fetch(
            `/api/output?process_id=${encodeURIComponent(currentProcessId)}`
        );

        const result = await response.json();

        if (!response.ok) {
            terminal.textContent += "\n" + (result.output || result.error);
            polling = false;
            return;
        }

        if (result.output) {
            terminal.textContent += result.output;
            terminal.scrollTop = terminal.scrollHeight;
        }

        if (result.status === "finished") {
            terminal.textContent += "\nProgram finished.";
            polling = false;
            currentProcessId = null;
            return;
        }

        setTimeout(pollOutput, 150);

    } catch (error) {
        terminal.textContent += "\nOutput error: " + error.message;
        polling = false;
    }
}

runButton.addEventListener("click", async () => {
    runButton.disabled = true;

    terminal.textContent = "Program started...\n";
    inputBuffer = "";
    currentProcessId = null;
    polling = false;

    try {
        const response = await fetch("/api/start", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                language: languageSelect.value,
                code: codeEditor.value
            })
        });

        const result = await response.json();

        if (!response.ok || result.status === "error") {
            terminal.textContent = result.output || result.error;
            return;
        }

        currentProcessId = result.process_id;
        terminal.textContent = result.output || "Program started...\n";

        polling = true;
        terminal.focus();

        pollOutput();

    } catch (error) {
        terminal.textContent = "Request failed: " + error.message;
    } finally {
        runButton.disabled = false;
    }
});

codeEditor.value = starterCode.c;

terminal.setAttribute("tabindex", "0");

checkBackend();
