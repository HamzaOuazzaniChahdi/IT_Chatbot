import io
import sys
import traceback
import contextlib
import html


def execute_code(code, timeout=5):
    """
    Execute Python code in a restricted environment and return the result.
    
    Args:
        code (str): The Python code to execute
        timeout (int): Maximum execution time in seconds
        
    Returns:
        dict: A dictionary containing execution results and metadata
    """
    # Capture stdout and stderr
    stdout_capture = io.StringIO()
    stderr_capture = io.StringIO()
    
    # Result container
    result = {
        'output': '',
        'error': None,
        'execution_time': 0,
        'success': True
    }
    
    # Redirect stdout and stderr, then execute the code
    with contextlib.redirect_stdout(stdout_capture), contextlib.redirect_stderr(stderr_capture):
        try:
            # Create a restricted local namespace
            local_namespace = {}
            
            # Execute the code with a timeout
            exec(code, {"__builtins__": __builtins__}, local_namespace)
            
            # Get the output
            result['output'] = stdout_capture.getvalue()
            
            # Add any defined variables to the result
            result['variables'] = {k: repr(v) for k, v in local_namespace.items() 
                                 if not k.startswith('_') and k != 'contextlib'}
                
        except Exception as e:
            result['success'] = False
            result['error'] = {
                'type': type(e).__name__,
                'message': str(e),
                'traceback': traceback.format_exc()
            }
            result['output'] = stdout_capture.getvalue()
            if stderr_capture.getvalue():
                result['error']['stderr'] = stderr_capture.getvalue()
    
    return result


def format_result_as_html(result):
    """
    Format the execution result as HTML for display.
    
    Args:
        result (dict): The execution result from execute_code
        
    Returns:
        str: HTML representation of the result
    """
    html_output = []
    
    # Add the output section if there's any output
    if result['output']:
        html_output.append('<div class="sandbox-output">')
        html_output.append('<h3>Output:</h3>')
        html_output.append(f'<pre>{html.escape(result["output"])}</pre>')
        html_output.append('</div>')
    
    # Add variables section if there are any
    if 'variables' in result and result['variables']:
        html_output.append('<div class="sandbox-variables">')
        html_output.append('<h3>Variables:</h3>')
        html_output.append('<table class="variable-table">')
        html_output.append('<tr><th>Name</th><th>Value</th></tr>')
        for name, value in result['variables'].items():
            html_output.append(f'<tr><td>{html.escape(name)}</td><td>{html.escape(value)}</td></tr>')
        html_output.append('</table>')
        html_output.append('</div>')
    
    # Add error section if there was an error
    if not result['success'] and result['error']:
        html_output.append('<div class="sandbox-error">')
        html_output.append('<h3>Error:</h3>')
        html_output.append(f'<p class="error-type">{html.escape(result["error"]["type"])}: {html.escape(result["error"]["message"])}</p>')
        if 'traceback' in result['error']:
            html_output.append(f'<pre class="error-traceback">{html.escape(result["error"]["traceback"])}</pre>')
        html_output.append('</div>')
    
    return ''.join(html_output)