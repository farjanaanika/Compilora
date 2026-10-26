
const languageSelect = document.getElementById("language");
const codeEditor = document.getElementById("code");
const programInput = document.getElementById("programInput");
const terminal = document.getElementById("terminal");
const runButton = document.getElementById("runButton");

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
    programInput.value = "";
    terminal.textContent = "Ready to compile and run.";
});

async function checkBackend() {
    try {
        const response = await fetch("/api/health");
        const result = await response.json();
        terminal.textContent = result.message;
    } catch {
        terminal.textContent = "Cannot connect to the backend.";
    }
}

runButton.addEventListener("click", async () => {
    runButton.disabled = true;
    terminal.textContent = "Compiling and running...";

    try {
        const response = await fetch("/api/run", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                language: languageSelect.value,
                code: codeEditor.value,
                input: programInput.value
            })
        });

        const result = await response.json();
        terminal.textContent = result.output || result.error || "No output.";
    } catch (error) {
        terminal.textContent = "Request failed: " + error.message;
    } finally {
        runButton.disabled = false;
    }
});

codeEditor.value = starterCode.c;
checkBackend();
