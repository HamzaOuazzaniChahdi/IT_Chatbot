// Code Sandbox JavaScript

// Global variables
let codeEditor;
let codeHistory = [];

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    // Initialize CodeMirror
    initCodeEditor();
    
    // Setup event listeners
    setupEventListeners();
    
    // Load code history
    loadCodeHistory();
});

// Initialize CodeMirror editor
function initCodeEditor() {
    codeEditor = CodeMirror(document.getElementById('codeEditor'), {
        mode: 'python',
        theme: 'dracula',
        lineNumbers: true,
        indentUnit: 4,
        smartIndent: true,
        tabSize: 4,
        indentWithTabs: false,
        lineWrapping: true,
        extraKeys: {
            "Tab": (cm) => cm.execCommand("indentMore"),
            "Shift-Tab": (cm) => cm.execCommand("indentLess"),
            "Ctrl-Enter": runCode
        }
    });
    
    // Set default content
    codeEditor.setValue('# Écrivez votre code Python ici\n# Appuyez sur Ctrl+Enter pour l\'exécuter\n\n');
}

// Setup all event listeners
function setupEventListeners() {
    // Run code button
    document.getElementById('runButton').addEventListener('click', runCode);
    
    // Clear code button
    document.getElementById('clearButton').addEventListener('click', () => {
        codeEditor.setValue('');
        codeEditor.focus();
    });
    
    // Clear output button
    document.getElementById('clearOutputButton').addEventListener('click', clearOutput);
    
    // Insert example button
    document.getElementById('insertExampleButton').addEventListener('click', insertExample);
    
    // Clear history button
    document.getElementById('clearHistoryButton').addEventListener('click', clearHistory);
}

// Execute code
function runCode() {
    const code = codeEditor.getValue();
    if (!code.trim()) return;
    
    // Show loading state
    showLoadingOutput();
    
    // Send code to server
    fetch('/execute_code', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ code })
    })
    .then(response => response.json())
    .then(result => {
        // Display the result
        displayOutput(result);
        
        // Refresh history
        loadCodeHistory();
    })
    .catch(error => {
        // Show error
        const outputDisplay = document.getElementById('outputDisplay');
        outputDisplay.innerHTML = `
            <div class="sandbox-error">
                <h3>Error:</h3>
                <p class="error-type">Erreur de connexion: ${error.message}</p>
            </div>
        `;
    });
}

// Display code execution result
function displayOutput(result) {
    const outputDisplay = document.getElementById('outputDisplay');
    
    if (result.html_result) {
        outputDisplay.innerHTML = result.html_result;
    } else {
        // Fallback if html_result is not available
        let outputHtml = '';
        
        if (result.output) {
            outputHtml += `
                <div class="sandbox-output">
                    <h3>Output:</h3>
                    <pre>${escapeHtml(result.output)}</pre>
                </div>
            `;
        }
        
        if (!result.success && result.error) {
            outputHtml += `
                <div class="sandbox-error">
                    <h3>Error:</h3>
                    <p class="error-type">${escapeHtml(result.error.type)}: ${escapeHtml(result.error.message)}</p>
                    ${result.error.traceback ? `<pre class="error-traceback">${escapeHtml(result.error.traceback)}</pre>` : ''}
                </div>
            `;
        }
        
        outputDisplay.innerHTML = outputHtml || `
            <div class="output-placeholder">
                <i class="fas fa-code"></i>
                <p>No output</p>
            </div>
        `;
    }
}

// Show loading state in output
function showLoadingOutput() {
    const outputDisplay = document.getElementById('outputDisplay');
    outputDisplay.innerHTML = `
        <div class="output-placeholder">
            <div class="typing-indicator">
                <span></span>
                <span></span>
                <span></span>
            </div>
            <p>Exécution du code...</p>
        </div>
    `;
}

// Clear output
function clearOutput() {
    const outputDisplay = document.getElementById('outputDisplay');
    outputDisplay.innerHTML = `
        <div class="output-placeholder">
            <i class="fas fa-code"></i>
            <p>Exécutez du code pour voir les résultats ici</p>
        </div>
    `;
}

// Insert example code
function insertExample() {
    const exampleCode = `# Exemple de code Python
import math
from datetime import datetime

# Afficher la date et l'heure actuelles
current_time = datetime.now()
print(f"Date et heure actuelles: {current_time}")

# Calculer quelques valeurs mathématiques
radius = 5
area = math.pi * radius ** 2
print(f"L'aire d'un cercle de rayon {radius} est {area:.2f}")

# Définir une fonction
def fibonacci(n):
    """Retourne le n-ième nombre de Fibonacci."""
    if n <= 1:
        return n
    else:
        return fibonacci(n-1) + fibonacci(n-2)

# Afficher les 10 premiers nombres de Fibonacci
print("\\nSuite de Fibonacci:")
for i in range(10):
    print(f"fibonacci({i}) = {fibonacci(i)}")
`;
    
    codeEditor.setValue(exampleCode);
    codeEditor.focus();
}

// Load code execution history
function loadCodeHistory() {
    fetch('/code_history')
    .then(response => response.json())
    .then(history => {
        // Update the history display
        displayHistory(history);
    })
    .catch(error => {
        console.error('Error loading history:', error);
    });
}

// Display code history
function displayHistory(history) {
    const historyContainer = document.getElementById('historyItems');
    historyContainer.innerHTML = '';
    
    if (history.length === 0) {
        historyContainer.innerHTML = `
            <div class="history-empty">
                <p>Aucun historique disponible</p>
            </div>
        `;
        return;
    }
    
    // Reverse to show newest first
    history.reverse().forEach(item => {
        const historyItem = document.createElement('div');
        historyItem.className = 'history-item';
        historyItem.setAttribute('data-id', item.id);
        
        // Format timestamp
        const timestamp = new Date(item.timestamp);
        const formattedTime = timestamp.toLocaleTimeString();
        
        // Determine success status
        const isSuccess = item.result.success;
        const statusClass = isSuccess ? 'success' : 'error';
        const statusText = isSuccess ? 'Succès' : 'Erreur';
        
        historyItem.innerHTML = `
            <div class="history-item-header">
                <span class="history-timestamp">${formattedTime}</span>
                <span class="history-status ${statusClass}">${statusText}</span>
            </div>
            <div class="history-code">${escapeHtml(item.code)}</div>
        `;
        
        // Add click event to load this code
        historyItem.addEventListener('click', () => {
            codeEditor.setValue(item.code);
            codeEditor.focus();
        });
        
        historyContainer.appendChild(historyItem);
    });
}

// Clear history
function clearHistory() {
    if (confirm('Êtes-vous sûr de vouloir effacer tout l\'historique ?')) {
        // Clear history in UI
        document.getElementById('historyItems').innerHTML = `
            <div class="history-empty">
                <p>Aucun historique disponible</p>
            </div>
        `;
        
        // Clear history in session
        fetch('/code_history', {
            method: 'DELETE'
        })
        .catch(error => {
            console.error('Error clearing history:', error);
        });
    }
}

// Helper function to escape HTML
function escapeHtml(unsafe) {
    return unsafe
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}