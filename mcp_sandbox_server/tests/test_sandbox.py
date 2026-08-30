from mcp_sandbox_server.sandbox import execute_command, apply_patch, reset_sandbox

def test_execute_command():
    reset_sandbox()
    res = execute_command('echo "hello world"')
    assert res.strip() == 'hello world'

def test_execute_command_failure():
    res = execute_command('ls /nonexistent_dir')
    assert 'Error (Exit Code' in res
    assert 'No such file or directory' in res

def test_apply_patch():
    # Patch a file
    res = apply_patch('test_file.py', 'print("patched")')
    assert 'Error' not in res
    
    # Read it back
    res = execute_command('cat test_file.py')
    assert res.strip() == 'print("patched")'

def test_reset():
    res = reset_sandbox()
    assert "Sandbox reset successfully" in res
