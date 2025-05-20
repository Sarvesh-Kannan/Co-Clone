# Co-Clone Examples

This directory contains examples to demonstrate Co-Clone's features.

## Function Change Tracking Example

The following examples demonstrate how Co-Clone can track function changes and suggest updates:

### Files:
- `app_example.py`: Contains the main function definitions
- `data_processor.py`: Contains code that uses functions from app_example.py

### Testing Function Change Tracking:

1. Start Co-Clone and go to the "Function Change Tracking" tab.

2. Click "Scan Codebase" to identify all function definitions and usages.

3. Make a change to a function signature in `app_example.py`. For example, change:
   ```python
   def process_data(data, threshold=0.5):
   ```
   to:
   ```python
   def process_data(data, threshold=0.5, normalize=False):
   ```

4. Copy the entire modified function to the Function Code Input textbox.

5. Set the File Path to `examples/app_example.py`.

6. Click "Detect Function Changes".

7. Co-Clone will detect that the function signature has changed and will suggest updates to all usages of this function in `data_processor.py`.

## Other Examples

### Python Example
`python_example.py` demonstrates code completion for Python functions, including:
- A complete factorial function
- An incomplete Fibonacci sequence function that Co-Clone can complete

### JavaScript Example
`javascript_example.js` demonstrates code completion for JavaScript classes, including:
- A Todo app with several implemented methods
- An incomplete filter method that Co-Clone can implement based on context 