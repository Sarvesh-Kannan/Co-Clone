# Co-Clone: AI Coding Assistant

Co-Clone is a local AI coding assistant that mimics the functionality of GitHub Copilot. It provides intelligent code completions and context-aware implementations using a local LLM (deepseek-coder:6.7b) running via Ollama.

## Features

- **Code Completion**: Completes your code as you type, similar to GitHub Copilot.
- **Context-Aware Completion**: Understands the entire codebase to provide relevant implementations for incomplete code segments.
- **Function Change Tracking**: Monitors function signature changes and suggests updates to all dependent code.
- **HTTP/2 Streaming**: Uses HTTP/2 with streaming responses for low-latency code suggestions.
- **Request Cancellation**: Efficiently cancels requests when typing continues, improving resource usage.
- **Multi-region Architecture**: Simulates geographic routing for optimal latency based on user location.
- **Long-lived Connections**: Maintains persistent connections for reduced latency and improved performance.
- **Local Processing**: All processing is done locally using Ollama, ensuring privacy and no data sharing.

## Architecture

Co-Clone implements a proxy-based architecture inspired by GitHub Copilot's design:

![Architecture Diagram](https://mermaid.ink/img/pako:eNp1kU1rwzAMhv-K0WmFJXEcZ1kPg9F2h7HD2A5jt8qRm5jFTmofhhj977PbUjYY6CBI7_NoJF8QYyZQQI97ynCGE3HGKMXmSLyJZbHYDNlgIsmEo5CuB8p0GrR5oP64y_3DLcXUDGo2N7jVPUeDdxXYQ8kT_eDTEFtMKrXTzVZK1Z5U-wWwpd5R7SX8I0FKZ3tUC2P4Xy7JBu-pT4LQljKnOGx95jdPgWKxYWyFvSSdWkrC4YbzZlqrDqEHOkdm8Z2vRBXzRKJyA_bVFTwDU8cZCpiVvSghlSb6c1jh5_q-KCwUruoaHv9YuS0UsqQ08nOlDQcM0PGMlOdwdNHf40iO8DWW49xROFzRu2O8GRTaO_gEqXRdKZ6LFbys19qPaXPzC_NXXSM?type=png)

1. **Proxy Layer**: A FastAPI-based proxy service that handles authentication, request routing, and cancellation.
2. **Geographic Routing**: Simulates DNS-based routing to direct users to the closest proxy instance.
3. **Connection Pooling**: Maintains persistent HTTP/2 connections between components.
4. **Streaming Completions**: Delivers real-time suggestions as they're generated, not waiting for the entire response.
5. **Request Cancellation**: Efficiently cancels in-flight requests when users continue typing.

## Prerequisites

- Python 3.6 or higher
- [Ollama](https://ollama.ai/) installed locally
- The deepseek-coder:6.7b model pulled in Ollama

## Installation

1. Clone this repository:
   ```
   git clone https://github.com/yourusername/co-clone.git
   cd co-clone
   ```

2. Create and activate a virtual environment:
   ```
   python -m venv venv
   
   # On Windows
   .\venv\Scripts\Activate.ps1  # PowerShell
   # OR
   .\venv\Scripts\activate.bat  # Command Prompt
   
   # On macOS/Linux
   source venv/bin/activate
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Make sure Ollama is running and the deepseek-coder:6.7b model is pulled:
   ```
   ollama pull deepseek-coder:6.7b
   ```

## Usage

### Standard Mode

1. Start the application:
   ```
   python app.py
   ```

2. Open your web browser and navigate to:
   - Web Form Interface: `http://localhost:5000`
   - IDE-like Interface: `http://localhost:5000/ide`

### Multi-region Mode (Advanced)

To test the multi-region proxy architecture with simulated geographic routing:

1. Start the application with the run script:
   ```
   python run.py --multi-region
   ```

   This will start:
   - Flask app on port 5000
   - Four proxy instances on ports 8000-8003 simulating different regions (us-west, us-east, eu-west, ap-east)

2. Access the IDE interface at `http://localhost:5000/ide`

3. You can simulate different user locations by adding a location parameter:
   ```
   http://localhost:5000/ide?location=eu
   ```

### IDE-like Interface Features

The IDE interface now includes:

- Real-time streaming completions with ghost text
- Intelligent typing prediction to reduce unnecessary requests
- HTTP/2-based streaming for low-latency suggestions
- Request cancellation when typing continues
- Multiple file tabs with proper tab management
- Enhanced function change detection and notification
- File upload and management capabilities

### Example Usage

#### Code Completion
Paste this incomplete function into the "Code Completion" text area:
```python
def sort_by_frequency(arr):
    """
    Sort an array of elements by their frequency of occurrence.
    Elements with higher frequency come first.
    
    Args:
        arr (list): List of elements
        
    Returns:
        list: Sorted list by frequency
    """
    # Code implementation here
```

#### Context-Aware Completion
Paste the full JavaScript Todo application from `examples/javascript_example.js` into the context area, and the incomplete method into the "Incomplete part" area:
```javascript
/**
 * Filter todos based on their completed status
 * @param {boolean} completed - Filter for completed todos
 */
// This method is incomplete - Co-Clone can complete it
```

#### Function Change Tracking
1. Click "Scan Codebase" to detect all functions in your codebase
2. Update a function signature in your code
3. Paste the updated function into the Function Change Tracking tab
4. Click "Detect Function Changes" to get suggestions for all dependent code

## How It Works

Co-Clone's architecture is based on these key components:

1. **FastAPI Proxy Service**: Acts as an intermediary between the IDE and the LLM, handling authentication, connection pooling, and request cancellation.

2. **Geographic Router**: Simulates DNS-based routing to direct users to the closest proxy instance based on their location.

3. **HTTP/2 Streaming**: Utilizes HTTP/2 with streaming responses to provide real-time completions with minimal latency.

4. **Token-based Authentication**: Uses short-lived tokens (10 minutes) to authenticate requests to the proxy service.

5. **Request Cancellation**: Efficiently cancels in-flight requests when users continue typing, preserving resources.

6. **Typing Prediction**: Analyzes typing patterns to predict when a user has paused and is ready for a suggestion.

## Technical Highlights

- **HTTP/2 Benefits**: Multiplexing requests over a single connection, avoiding the overhead of establishing new connections for each request.
  
- **Connection Pooling**: Maintains persistent connections between components, reducing latency by avoiding connection setup costs.

- **Request Cancellation**: Unlike standard HTTP, implements cancellation that preserves connection state.

- **Proxy-based Architecture**: Separates authentication and request routing from the core completion logic, allowing for better scaling and geographic distribution.

- **Streaming Responses**: Delivers completion suggestions as they're generated, not waiting for the entire response.

## Limitations

- Performance is dependent on your hardware capabilities since processing is done locally.
- The quality of completions may not match GitHub Copilot as it uses a smaller, locally-run model.
- The geographic routing simulation uses local ports rather than actual distributed servers.

## Roadmap

- IDE integrations (VS Code, JetBrains IDEs)
- Support for more programming languages and frameworks
- Performance optimizations
- Actual distributed proxy instances for true geographic distribution
- Enhanced streaming and cancellation optimizations

## License

MIT 