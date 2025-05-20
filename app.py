from flask import Flask, request, jsonify, render_template, Response, stream_with_context
import os
import re
import glob
import json
import time
import uuid
import requests
from collections import defaultdict
from dotenv import load_dotenv
import ollama
import httpx
import asyncio
from concurrent.futures import ThreadPoolExecutor

# Local modules
try:
    from geo_router import get_proxy_for_location
except ImportError:
    # Mock function if the geo_router module is not available
    def get_proxy_for_location(location=None):
        return {
            "token_url": "http://localhost:8000/token",
            "region": "local",
            "latency": 0.01,
            "url": "http://localhost:8000"
        }

# Load environment variables (silently pass if .env doesn't exist)
load_dotenv(verbose=False)

app = Flask(__name__)

# Initialize Ollama client with default if environment variable isn't set
client = ollama.Client(host=os.getenv("OLLAMA_HOST", "http://localhost:11434"))
MODEL = os.getenv("OLLAMA_MODEL", "deepseek-coder:6.7b")

# Store function definitions and usages
function_definitions = {}  # {function_name: {'file': file_path, 'code': code, 'signature': signature}}
function_usages = defaultdict(list)  # {function_name: [{'file': file_path, 'line': line_number, 'code': usage_code}]}

# Executor for running async tasks
executor = ThreadPoolExecutor(max_workers=10)

# Cache for active tokens
active_tokens = {}

def extract_python_functions(file_path):
    """Extract Python function definitions and usages from a file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find function definitions
    def_pattern = re.compile(r'def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\((.*?)\)(?:\s*->.*?)?:', re.DOTALL)
    for match in def_pattern.finditer(content):
        func_name = match.group(1)
        func_params = match.group(2).strip()
        
        # Find the function body
        start_pos = match.end()
        lines = content[start_pos:].split('\n')
        
        # Extract indented function body
        func_body_lines = []
        for line in lines:
            if line.strip() == '' or line.startswith(' ') or line.startswith('\t'):
                func_body_lines.append(line)
            else:
                break
        
        func_def = f"def {func_name}({func_params}):"
        func_body = '\n'.join(func_body_lines)
        func_code = func_def + '\n' + func_body
        
        function_definitions[func_name] = {
            'file': file_path,
            'code': func_code,
            'signature': func_params
        }
    
    # Find function usages
    lines = content.split('\n')
    for i, line in enumerate(lines):
        for func_name in function_definitions:
            # Simple pattern to find function calls
            call_pattern = re.compile(r'\b' + re.escape(func_name) + r'\s*\(')
            if call_pattern.search(line) and 'def ' + func_name not in line:
                function_usages[func_name].append({
                    'file': file_path,
                    'line': i + 1,
                    'code': line.strip()
                })

def extract_js_functions(file_path):
    """Extract JavaScript function definitions and usages from a file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find function/method definitions
    # Function declarations
    func_pattern = re.compile(r'function\s+([a-zA-Z_$][a-zA-Z0-9_$]*)\s*\((.*?)\)', re.DOTALL)
    # Method definitions
    method_pattern = re.compile(r'(?:async\s+)?([a-zA-Z_$][a-zA-Z0-9_$]*)\s*\((.*?)\)\s*{', re.DOTALL)
    # Arrow functions
    arrow_pattern = re.compile(r'const\s+([a-zA-Z_$][a-zA-Z0-9_$]*)\s*=\s*(?:async\s+)?\((.*?)\)\s*=>', re.DOTALL)
    
    # Process function declarations
    for pattern in [func_pattern, method_pattern, arrow_pattern]:
        for match in pattern.finditer(content):
            func_name = match.group(1)
            func_params = match.group(2).strip()
            
            if func_name in ['if', 'for', 'while', 'switch']:
                continue  # Skip control structures
                
            # Find function body (simplified approach)
            function_definitions[func_name] = {
                'file': file_path,
                'code': match.group(0),
                'signature': func_params
            }
    
    # Find function usages
    lines = content.split('\n')
    for i, line in enumerate(lines):
        for func_name in function_definitions:
            # Simple pattern to find function calls
            call_pattern = re.compile(r'\b' + re.escape(func_name) + r'\s*\(')
            if call_pattern.search(line) and not re.search(r'(function|const)\s+' + re.escape(func_name), line):
                function_usages[func_name].append({
                    'file': file_path,
                    'line': i + 1,
                    'code': line.strip()
                })

def scan_codebase(directory='.', file_patterns=None):
    """Scan the codebase to extract function definitions and usages."""
    if file_patterns is None:
        file_patterns = ['**/*.py', '**/*.js', '**/*.ts']
    
    # Reset current data
    function_definitions.clear()
    function_usages.clear()
    
    # Add examples directory explicitly
    directories_to_scan = [directory, 'examples']
    
    for scan_dir in directories_to_scan:
        for pattern in file_patterns:
            for file_path in glob.glob(os.path.join(scan_dir, pattern), recursive=True):
                # Skip virtual environment files
                if 'venv' in file_path.split(os.sep):
                    continue
                    
                # Skip node_modules if exists
                if 'node_modules' in file_path.split(os.sep):
                    continue
                    
                # Process based on file extension
                if file_path.endswith('.py'):
                    extract_python_functions(file_path)
                elif file_path.endswith('.js') or file_path.endswith('.ts'):
                    extract_js_functions(file_path)
    
    return {
        'definitions': function_definitions,
        'usages': {k: v for k, v in function_usages.items()}
    }

@app.route('/')
def index():
    # Scan codebase on initial page load
    scan_codebase()
    return render_template('index.html')

@app.route('/ide')
def ide_view():
    # Scan codebase on IDE load
    scan_codebase()
    return render_template('ide.html')

@app.route('/read-file')
def read_file():
    file_path = request.args.get('path')
    if not file_path:
        return jsonify({"error": "No file path provided"}), 400
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return jsonify({"content": content})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/proxy/token')
def get_token():
    """Get a token from the appropriate proxy instance based on user location."""
    # Get user location (would normally be detected from IP or user settings)
    location = request.args.get('location', 'us')
    
    try:
        # Get the appropriate proxy instance for the user's location
        proxy_info = get_proxy_for_location(location)
        
        # In a real implementation, we would make a request to the proxy's token endpoint
        # For the demo, we'll generate a token locally
        token = str(uuid.uuid4())
        expires_at = int(time.time() + 600)  # 10 minutes
        
        # Store token in cache
        active_tokens[token] = {
            "expires_at": expires_at,
            "proxy_url": proxy_info["url"]
        }
        
        return jsonify({
            "token": token,
            "expires_at": expires_at,
            "region": proxy_info["region"]
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/proxy/v1/completions', methods=['POST'])
def proxy_completion():
    """Proxy a completion request to the appropriate copilot-proxy instance."""
    # Get auth token from header
    auth_header = request.headers.get('Authorization', '')
    token = auth_header.replace('Bearer ', '')
    
    if not token or token not in active_tokens:
        return jsonify({"error": "Unauthorized"}), 401
    
    # Check if token has expired
    token_info = active_tokens.get(token)
    if token_info["expires_at"] < time.time():
        active_tokens.pop(token, None)
        return jsonify({"error": "Token expired"}), 401
    
    # Generate a unique request ID
    request_id = str(uuid.uuid4())
    
    # Get completion request data
    data = request.json
    prompt = data.get('prompt', '')
    
    def generate():
        """Generator function for streaming the completion response."""
        try:
            # Stream from Ollama
            stream = client.generate(
                model=MODEL,
                prompt=prompt,
                stream=True,
                options={
                    "temperature": data.get('temperature', 0.7),
                    "num_predict": data.get('max_tokens', 512)
                }
            )
            
            for chunk in stream:
                response_text = chunk["response"]
                if response_text:
                    yield f"data: {response_text}\n\n"
            
            # End of stream
            yield "data: [DONE]\n\n"
        except Exception as e:
            yield f"data: {{\"error\": \"{str(e)}\"}}\n\n"
    
    return Response(
        stream_with_context(generate()),
        content_type='text/event-stream',
        headers={
            'X-Request-ID': request_id,
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive'
        }
    )

@app.route('/proxy/v1/completions/<request_id>', methods=['DELETE'])
def cancel_completion(request_id):
    """Cancel an ongoing completion request."""
    # Get auth token from header
    auth_header = request.headers.get('Authorization', '')
    token = auth_header.replace('Bearer ', '')
    
    if not token or token not in active_tokens:
        return jsonify({"error": "Unauthorized"}), 401
    
    # In a real implementation, this would communicate with the proxy to cancel the request
    # For the demo, we'll just return success
    return jsonify({
        "status": "cancelled",
        "request_id": request_id
    })

@app.route('/complete', methods=['POST'])
def complete_code():
    data = request.json
    code = data.get('code', '')
    cursor_position = data.get('position', len(code))
    
    # Create a prompt that instructs the model to complete the code
    prompt = f"""
    You are a code completion assistant that provides intelligent code completions.
    Complete the following code snippet:
    ```
    {code}
    ```
    The cursor is at position {cursor_position}.
    Please provide only the code completion, no explanations or markdown.
    """
    
    try:
        response = client.generate(model=MODEL, prompt=prompt)
        completion = response['response'].strip()
        
        # Clean up the response to only include the code completion
        if "```" in completion:
            completion = completion.split("```")[1]
            if completion.startswith(("python", "javascript", "typescript", "html", "css")):
                completion = "\n".join(completion.split("\n")[1:])
        
        return jsonify({"completion": completion})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/understand', methods=['POST'])
def understand_code():
    data = request.json
    code = data.get('code', '')
    incomplete_part = data.get('incomplete_part', '')
    
    # Create a prompt that instructs the model to understand and complete the code
    prompt = f"""
    You are a code completion assistant that understands code contexts.
    Analyze the following complete code:
    ```
    {code}
    ```
    
    The following part needs to be completed or fixed:
    ```
    {incomplete_part}
    ```
    
    Based on the context of the entire codebase, provide the appropriate implementation.
    Please provide only the code completion, no explanations or markdown.
    """
    
    try:
        response = client.generate(model=MODEL, prompt=prompt)
        completion = response['response'].strip()
        
        # Clean up the response to only include the code implementation
        if "```" in completion:
            completion = completion.split("```")[1]
            if completion.startswith(("python", "javascript", "typescript", "html", "css")):
                completion = "\n".join(completion.split("\n")[1:])
        
        return jsonify({"implementation": completion})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/detect-changes', methods=['POST'])
def detect_function_changes():
    """Detect changes in function signatures and suggest updates in real-time."""
    data = request.json
    file_path = data.get('file_path', '')
    code = data.get('code', '')
    
    # Store the original codebase state
    original_definitions = dict(function_definitions)
    original_usages = defaultdict(list, {k: list(v) for k, v in function_usages.items()})
    original_function_names = set(original_definitions.keys())
    
    # Extract functions from the current code (without writing to file)
    extracted_functions = {}
    function_signature_changes = []
    
    if file_path.endswith('.py'):
        # Extract Python functions from the current code
        def_pattern = re.compile(r'def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\((.*?)\)(?:\s*->.*?)?:', re.DOTALL)
        for match in def_pattern.finditer(code):
            func_name = match.group(1)
            func_params = match.group(2).strip()
            
            # Find the function body
            start_pos = match.end()
            lines = code[start_pos:].split('\n')
            
            # Extract indented function body
            func_body_lines = []
            for line in lines:
                if line.strip() == '' or line.startswith(' ') or line.startswith('\t'):
                    func_body_lines.append(line)
                else:
                    break
            
            func_def = f"def {func_name}({func_params}):"
            func_body = '\n'.join(func_body_lines)
            func_code = func_def + '\n' + func_body
            
            extracted_functions[func_name] = {
                'file': file_path,
                'code': func_code,
                'signature': func_params
            }
            
            # Check if this is a modified function
            if func_name in original_definitions:
                old_params = original_definitions[func_name]['signature']
                if old_params != func_params:
                    function_signature_changes.append({
                        'name': func_name,
                        'old_signature': old_params,
                        'new_signature': func_params,
                        'file': file_path,
                        'detailed_changes': analyze_parameter_changes(old_params, func_params)
                    })
    
    elif file_path.endswith(('.js', '.ts')):
        # Extract JavaScript/TypeScript functions
        patterns = [
            re.compile(r'function\s+([a-zA-Z_$][a-zA-Z0-9_$]*)\s*\((.*?)\)', re.DOTALL),
            re.compile(r'(?:async\s+)?([a-zA-Z_$][a-zA-Z0-9_$]*)\s*\((.*?)\)\s*{', re.DOTALL),
            re.compile(r'const\s+([a-zA-Z_$][a-zA-Z0-9_$]*)\s*=\s*(?:async\s+)?\((.*?)\)\s*=>', re.DOTALL)
        ]
        
        for pattern in patterns:
            for match in pattern.finditer(code):
                func_name = match.group(1)
                func_params = match.group(2).strip()
                
                # Skip control structures
                if func_name in ['if', 'for', 'while', 'switch']:
                    continue
                
                # Store the extracted function
                extracted_functions[func_name] = {
                    'file': file_path,
                    'code': match.group(0),
                    'signature': func_params
                }
                
                # Check if this is a modified function
                if func_name in original_definitions:
                    old_params = original_definitions[func_name]['signature']
                    if old_params != func_params:
                        function_signature_changes.append({
                            'name': func_name,
                            'old_signature': old_params,
                            'new_signature': func_params,
                            'file': file_path,
                            'detailed_changes': analyze_parameter_changes(old_params, func_params)
                        })
    
    # Detect renamed functions by comparing original and extracted function lists
    extracted_function_names = set(extracted_functions.keys())
    removed_functions = original_function_names - extracted_function_names
    added_functions = extracted_function_names - original_function_names
    
    # Try to match renamed functions based on signature and file similarity
    renamed_functions = []
    
    for removed_func in removed_functions:
        if file_path == original_definitions[removed_func]['file']:
            # Find possible matches among added functions
            for added_func in added_functions:
                if file_path == extracted_functions[added_func]['file']:
                    old_sig = original_definitions[removed_func]['signature']
                    new_sig = extracted_functions[added_func]['signature']
                    
                    # If signatures are similar or identical, it's likely a rename
                    if old_sig == new_sig or similarity_score(old_sig, new_sig) > 0.7:
                        renamed_functions.append({
                            'old_name': removed_func,
                            'new_name': added_func,
                            'file': file_path,
                            'old_signature': old_sig,
                            'new_signature': new_sig,
                        })
                        # Remove from added and removed to avoid duplicate entries
                        if added_func in added_functions:
                            added_functions.remove(added_func)
                        if removed_func in removed_functions:
                            removed_functions.remove(removed_func)
                        break
    
    # Update function definitions with the new extracted functions
    for func_name, func_info in extracted_functions.items():
        function_definitions[func_name] = func_info
    
    # Generate intelligent update suggestions for all affected usages
    update_suggestions = []
    
    # Process renamed functions first
    for rename in renamed_functions:
        old_name = rename['old_name']
        new_name = rename['new_name']
        
        # Find all usages of the old function name
        usages = original_usages.get(old_name, [])
        
        for usage in usages:
            # Skip usages in the current file as they might be updated already
            if usage['file'] == file_path:
                continue
                
            # Create a suggestion for the renamed function
            old_code = usage['code']
            # Replace the function name in the code
            new_code = old_code.replace(old_name, new_name)
            
            update_suggestions.append({
                'function': old_name,
                'new_function': new_name,
                'file': usage['file'],
                'line': usage['line'],
                'old_code': old_code,
                'new_code': new_code,
                'original_file': file_path,
                'change_type': 'rename',
                'detailed_changes': {
                    'old_name': old_name,
                    'new_name': new_name
                }
            })
            
            # Also update the imports if needed
            if old_name != new_name and is_imported_function(usage['file'], old_name):
                update_suggestions.append({
                    'function': old_name,
                    'new_function': new_name,
                    'file': usage['file'],
                    'line': find_import_line(usage['file'], old_name),
                    'old_code': get_import_line(usage['file'], old_name),
                    'new_code': update_import_line(usage['file'], old_name, new_name),
                    'original_file': file_path,
                    'change_type': 'import_update',
                    'detailed_changes': {
                        'old_name': old_name,
                        'new_name': new_name
                    }
                })
    
    # Process signature changes
    for func_change in function_signature_changes:
        func_name = func_change['name']
        
        # Find all usages of this function
        usages = original_usages.get(func_name, [])
        
        for usage in usages:
            # Skip usages in the current file as they might be updated already
            if usage['file'] == file_path:
                continue
                
            # Generate suggestion for updating the usage
            suggestion = generate_usage_update_suggestion(
                func_name=func_name,
                usage_code=usage['code'],
                old_signature=func_change['old_signature'],
                new_signature=func_change['new_signature'],
                detailed_changes=func_change['detailed_changes']
            )
            
            update_suggestions.append({
                'function': func_name,
                'file': usage['file'],
                'line': usage['line'],
                'old_code': usage['code'],
                'new_code': suggestion,
                'original_file': func_change['file'],
                'change_type': 'signature_update',
                'detailed_changes': func_change['detailed_changes']
            })
    
    return jsonify({
        "update_suggestions": update_suggestions,
        "changed_functions": function_signature_changes,
        "renamed_functions": renamed_functions,
        "function_definitions": function_definitions,
        "function_usages": {k: v for k, v in function_usages.items()}
    })

def analyze_parameter_changes(old_params, new_params):
    """Analyze what exactly changed in the function parameters."""
    old_param_list = [p.strip() for p in old_params.split(',')] if old_params else []
    new_param_list = [p.strip() for p in new_params.split(',')] if new_params else []
    
    # Remove empty params
    old_param_list = [p for p in old_param_list if p]
    new_param_list = [p for p in new_param_list if p]
    
    # Parse parameters into name and default value
    def parse_param(param):
        if '=' in param:
            name, default = param.split('=', 1)
            return name.strip(), default.strip()
        else:
            return param.strip(), None
    
    old_parsed = [parse_param(p) for p in old_param_list]
    new_parsed = [parse_param(p) for p in new_param_list]
    
    old_param_names = [p[0] for p in old_parsed]
    new_param_names = [p[0] for p in new_parsed]
    
    # Analysis of changes
    added_params = [p for p in new_parsed if p[0] not in old_param_names]
    removed_params = [p for p in old_parsed if p[0] not in new_param_names]
    
    # Find params that had their default values changed
    changed_defaults = []
    for new_name, new_default in new_parsed:
        for old_name, old_default in old_parsed:
            if new_name == old_name and new_default != old_default:
                changed_defaults.append({
                    'name': new_name,
                    'old_default': old_default,
                    'new_default': new_default
                })
    
    # Check for reordering
    reordered = False
    common_params = [p for p in new_param_names if p in old_param_names]
    if len(common_params) > 1:
        old_indices = [old_param_names.index(p) for p in common_params]
        new_indices = [new_param_names.index(p) for p in common_params]
        reordered = old_indices != sorted(old_indices) or new_indices != sorted(new_indices)
    
    return {
        'added': added_params,
        'removed': removed_params,
        'changed_defaults': changed_defaults,
        'reordered': reordered
    }

def generate_usage_update_suggestion(func_name, usage_code, old_signature, new_signature, detailed_changes):
    """Generate a smart update suggestion based on detailed parameter changes."""
    # Create a specific prompt for the LLM to generate accurate update suggestion
    prompt = f"""
    A function signature has changed:
    
    Original: function {func_name}({old_signature})
    New: function {func_name}({new_signature})
    
    Detailed changes:
    - Added parameters: {detailed_changes['added']}
    - Removed parameters: {detailed_changes['removed']}
    - Changed defaults: {detailed_changes['changed_defaults']}
    - Parameters reordered: {detailed_changes['reordered']}
    
    Current usage:
    ```
    {usage_code}
    ```
    
    Update this usage to match the new function signature. Consider:
    1. If parameters were added with defaults, they may be omitted in the call
    2. If parameters were removed, remove them from the call
    3. If parameter order changed, ensure arguments are in the correct position
    4. If default values changed, update only if the call explicitly specified the old default
    
    Provide ONLY the updated code line with no explanations.
    """
    
    try:
        response = client.generate(model=MODEL, prompt=prompt)
        updated_code = response['response'].strip()
        
        # Clean up the response
        if "```" in updated_code:
            updated_code = updated_code.split("```")[1] if len(updated_code.split("```")) > 1 else updated_code
            if updated_code.startswith(("python", "javascript", "typescript")):
                updated_code = "\n".join(updated_code.split("\n")[1:])
            updated_code = updated_code.strip()
        
        # Clean ending backticks if present
        if updated_code.endswith("```"):
            updated_code = updated_code.rsplit("```", 1)[0].strip()
        
        return updated_code
    except Exception as e:
        print(f"Error generating update for {func_name}: {str(e)}")
        # Return original code as fallback
        return usage_code

@app.route('/scan-codebase', methods=['GET'])
def scan_codebase_route():
    """API endpoint to scan the codebase and return functions and their usages."""
    results = scan_codebase()
    return jsonify(results)

@app.route('/save-file', methods=['POST'])
def save_file():
    """Save file content to disk."""
    data = request.json
    file_path = data.get('file_path', '')
    content = data.get('content', '')
    
    if not file_path:
        return jsonify({"error": "No file path provided", "success": False}), 400
    
    try:
        # Create directories if they don't exist
        directory = os.path.dirname(file_path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e), "success": False}), 500

@app.route('/update-file', methods=['POST'])
def update_file():
    """Update a specific part of a file with new code."""
    data = request.json
    file_path = data.get('file_path', '')
    old_code = data.get('old_code', '')
    new_code = data.get('new_code', '')
    
    if not file_path or not old_code or not new_code:
        return jsonify({"error": "Missing parameters", "success": False}), 400
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Replace the old code with the new code
        if old_code in content:
            updated_content = content.replace(old_code, new_code)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(updated_content)
            
            return jsonify({"success": True})
        else:
            return jsonify({"error": "Original code not found in file", "success": False}), 404
    except Exception as e:
        return jsonify({"error": str(e), "success": False}), 500

@app.route('/real-time-complete', methods=['POST'])
def real_time_complete():
    """Provide real-time code completion suggestions."""
    data = request.json
    code = data.get('code', '')
    cursor_position = data.get('cursor_position', 0)
    file_path = data.get('file_path', '')
    
    # Create a prompt that focuses on real-time completion
    context_before = code[:cursor_position].strip()
    context_after = code[cursor_position:].strip()
    
    # Extract the current line being edited
    lines = context_before.split('\n')
    current_line = lines[-1] if lines else ""
    
    # Look for potential function calls that could be optimized
    function_context = {}
    function_suggestions = None
    
    # Check if we're typing a function name (or the start of one)
    function_name_match = re.search(r'(?:^|[^\w])(\w+)$', current_line)
    if function_name_match:
        partial_name = function_name_match.group(1)
        
        # Only process if the partial name is at least 2 characters long
        if len(partial_name) >= 2:
            # Find semantically related functions in the codebase
            similar_functions = []
            for func_name, func_info in function_definitions.items():
                # Check for prefix match
                if func_name.startswith(partial_name):
                    similar_functions.append((func_name, func_info, 0.9))  # High priority for prefix match
                # Check for substring match
                elif partial_name in func_name:
                    similar_functions.append((func_name, func_info, 0.7))  # Medium priority for substring match
                # Check for semantic similarity based on word parts
                elif any(word in func_name.lower() for word in partial_name.lower().split('_')):
                    similar_functions.append((func_name, func_info, 0.5))  # Lower priority for semantic match
            
            # Sort by priority
            similar_functions.sort(key=lambda x: x[2], reverse=True)
            
            if similar_functions:
                # Take the top match for function suggestion
                top_function = similar_functions[0][0]
                function_suggestions = {
                    "type": "function_name",
                    "name": top_function,
                    "signature": function_definitions[top_function]['signature']
                }
    
    # Check for function calls where we might need to provide parameter hints
    for func_name, func_info in function_definitions.items():
        if f"{func_name}(" in current_line:
            function_context[func_name] = func_info
    
    # Generate completion based on context
    completion = ""
    
    # If we're working with a function name, prioritize that
    if function_suggestions:
        completion = f"{function_suggestions['name']}({function_suggestions['signature']})"
        
        # Create a prompt to generate a better completion based on the function semantics
        prompt = f"""
        You are helping with code completion. The user is typing a function name: '{partial_name}'
        
        Most similar function in the codebase: {function_suggestions['name']}({function_suggestions['signature']})
        
        Based on the current code context, provide a completion that would help the user:
        
        ```
        {current_line}
        ```
        
        Complete only the current line. Don't explain, just provide the completion.
        """
        
        try:
            response = client.generate(model=MODEL, prompt=prompt)
            ai_completion = response['response'].strip()
            
            # Clean up the AI suggestion to just include the actual completion
            if ai_completion:
                completion = ai_completion
        except Exception as e:
            print(f"Error generating completion: {str(e)}")
    else:
        # Otherwise, use the context to generate a more general completion
        prompt = f"""
        You are assisting with real-time code completion. Complete the code based on the context:
        
        Previous code:
        ```
        {context_before}
        ```
        
        Current line: {current_line}
        
        Code after cursor:
        ```
        {context_after}
        ```
        
        Complete only the current line. Don't explain, just provide the completion.
        """
        
        try:
            response = client.generate(model=MODEL, prompt=prompt)
            completion = response['response'].strip()
            
            # Clean up the AI suggestion
            if completion.startswith("```"):
                completion = completion.split("```")[1]
                
                # Remove language identifier if present
                if completion.startswith(("python", "javascript", "typescript")):
                    completion = "\n".join(completion.split("\n")[1:])
                
                completion = completion.strip()
            
            # If completion still has ``` at the end, remove it
            if completion.endswith("```"):
                completion = completion.rsplit("```", 1)[0].strip()
        except Exception as e:
            print(f"Error generating completion: {str(e)}")
    
    return jsonify({
        "completion": completion,
        "function_hints": function_context,
        "function_suggestion": function_suggestions
    })

@app.route('/list-files')
def list_files():
    """List files in a directory with support for specific directories."""
    # Only show files from the examples directory
    result = {'files': []}
    
    # Process examples directory explicitly
    if os.path.exists('examples'):
        for root, dirs, files in os.walk('examples'):
            # Skip __pycache__ directories
            if '__pycache__' in root:
                continue
                
            for file in files:
                # Skip __pycache__ and other hidden files
                if '__pycache__' in file or file.startswith('.') or file.endswith('.pyc'):
                    continue
                    
                file_path = os.path.join(root, file)
                if os.path.isfile(file_path):
                    result['files'].append({
                        'path': file_path,
                        'name': file,
                        'type': os.path.splitext(file)[1][1:] if os.path.splitext(file)[1] else 'txt'
                    })
    
    return jsonify(result)

# Helper functions for handling renamed functions
def similarity_score(str1, str2):
    """Calculate a simple similarity score between two strings."""
    # Simple implementation - could be enhanced with more sophisticated algorithms
    if not str1 and not str2:
        return 1.0
    if not str1 or not str2:
        return 0.0
    
    # Count matching characters
    matches = sum(c1 == c2 for c1, c2 in zip(str1, str2))
    return 2.0 * matches / (len(str1) + len(str2))

def is_imported_function(file_path, function_name):
    """Check if a function is imported in a file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for import statements that include the function
        import_patterns = [
            re.compile(r'from\s+[a-zA-Z0-9_.]+\s+import\s+([^#\n]+)'),
            re.compile(r'import\s+([^#\n]+)')
        ]
        
        for pattern in import_patterns:
            for match in pattern.finditer(content):
                imports = match.group(1).strip()
                parts = [part.strip() for part in imports.split(',')]
                if function_name in parts:
                    return True
                if any(part.strip().endswith(' as ' + function_name) for part in parts):
                    return True
        
        return False
    except Exception:
        return False

def find_import_line(file_path, function_name):
    """Find the line number with the import statement for a function."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        for i, line in enumerate(lines):
            if ('import ' + function_name in line or 
                function_name + ',' in line or 
                ', ' + function_name in line or
                function_name + ' ' in line):
                return i + 1
        
        return 1  # Default to first line if not found
    except Exception:
        return 1

def get_import_line(file_path, function_name):
    """Get the import statement line for a function."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        for line in lines:
            if ('import ' + function_name in line or 
                function_name + ',' in line or 
                ', ' + function_name in line or
                function_name + ' ' in line):
                return line.strip()
        
        return ""
    except Exception:
        return ""

def update_import_line(file_path, old_name, new_name):
    """Update the import statement by replacing the old function name with the new one."""
    old_line = get_import_line(file_path, old_name)
    if not old_line:
        return ""
    
    # Handle different import formats
    if 'from ' in old_line and 'import ' in old_line:
        # from module import func1, func2
        parts = old_line.split('import ')
        import_part = parts[1].strip()
        imports = [imp.strip() for imp in import_part.split(',')]
        
        updated_imports = []
        for imp in imports:
            if imp.strip() == old_name:
                updated_imports.append(new_name)
            else:
                updated_imports.append(imp)
        
        return parts[0] + 'import ' + ', '.join(updated_imports)
    else:
        # Simple replacement for other cases
        return old_line.replace(old_name, new_name)

if __name__ == '__main__':
    app.run(debug=True) 