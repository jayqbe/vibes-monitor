# Troubleshooting

Common issues and solutions for Token Telemetry.

## Quick Diagnosis

### Check Proxy is Running

```bash
# Check if proxy process is running
ps aux | grep token_telemetry

# Or check the port
netstat -tuln | grep 8000  # Linux/macOS
lsof -i :8000             # macOS
```

### Check Database Exists

```bash
# List files in current directory
ls -la | grep telemetry.db

# Check if database has data
sqlite3 telemetry.db "SELECT COUNT(*) FROM calls;"
```

### Enable Debug Logging

```bash
# Start proxy with verbose logging
python -m token_telemetry.cli proxy --verbose

# Or set environment variable
export LOG_LEVEL=DEBUG
python -m token_telemetry.cli proxy
```

## Common Issues

### Proxy Server Won't Start

**Symptom:** `Address already in use` or `OSError: [Errno 48]`

**Solutions:**

1. **Port already in use:**
   ```bash
   # Find the process using port 8000
   lsof -i :8000
   
   # Kill the process
   kill <PID>
   
   # Or use a different port
   python -m token_telemetry.cli proxy --port 8001
   ```

2. **Permission denied:**
   ```bash
   # Try a port > 1024 (requires root for < 1024)
   python -m token_telemetry.cli proxy --port 8080
   
   # Or run as root (not recommended)
   sudo python -m token_telemetry.cli proxy --port 80
   ```

3. **Module not found:**
   ```bash
   # Install the package in development mode
   pip install -e .
   
   # Or add to PYTHONPATH
   export PYTHONPATH=/path/to/token-telemetry/src:$PYTHONPATH
   ```

### Vibe CLI Can't Connect to Proxy

**Symptom:** Vibe CLI hangs or returns connection errors.

**Solutions:**

1. **Verify proxy is running:**
   ```bash
   curl http://localhost:8000
   # Should return 404 or similar (proxy is working)
   ```

2. **Check environment variable:**
   ```bash
   echo $VIBE_API_ENDPOINT
   # Should show: http://localhost:8000
   
   # If not set:
   export VIBE_API_ENDPOINT=http://localhost:8000
   ```

3. **Check host binding:**
   ```bash
   # If you started with --host 0.0.0.0, use that IP
   export VIBE_API_ENDPOINT=http://0.0.0.0:8000
   
   # Or use 127.0.0.1
   export VIBE_API_ENDPOINT=http://127.0.0.1:8000
   ```

4. **Firewall blocking:**
   ```bash
   # Check firewall status
   sudo ufw status  # Ubuntu
   sudo firewall-cmd --list-all  # CentOS/RHEL
   
   # Allow the port
   sudo ufw allow 8000
   ```

### No Data in Reports

**Symptom:** Report shows 0 records or empty database.

**Solutions:**

1. **Verify API calls are being made:**
   ```bash
   # Start proxy with verbose logging
   python -m token_telemetry.cli proxy --verbose
   
   # In another terminal, make a test call
   curl -X POST http://localhost:8000/v1/chat/completions \
     -H "Content-Type: application/json" \
     -d '{"model": "mistral-tiny", "messages": [{"role": "user", "content": "test"}]}'
   
   # Check proxy logs for errors
   tail -f telemetry.log
   ```

2. **Check database directly:**
   ```bash
   sqlite3 telemetry.db "SELECT * FROM calls LIMIT 5;"
   ```

3. **Verify database path:**
   ```bash
   # Check what database path is being used
   python -c "from token_telemetry.config import load_config; c = load_config(); print(c.database.path)"
   
   # Start proxy with explicit database path
   python -m token_telemetry.cli proxy --config config/local.yaml
   ```

4. **Database permissions:**
   ```bash
   # Ensure current user can write to database location
   touch telemetry.db
   
   # Or change permissions
   chmod 666 telemetry.db
   ```

### Cost Calculation Issues

**Symptom:** Cost shows as $0.000000 or incorrect values.

**Solutions:**

1. **Check token counts:**
   ```bash
   # Generate report to see token counts
   python -m token_telemetry.cli report
   
   # If request_tokens and response_tokens are 0, the API response format may not be recognized
   ```

2. **Verify pricing configuration:**
   ```bash
   python -c "from token_telemetry.config import load_config; c = load_config(); print(c.pricing)"
   ```

3. **Custom model not in pricing:**
   ```yaml
   # Add to config/local.yaml
   pricing:
     your-model-name:
       input: 0.25
       output: 0.75
   ```

4. **Check API response format:**
   ```bash
   # Make a test call and check the response
   curl -X POST http://localhost:8000/v1/chat/completions \
     -H "Content-Type: application/json" \
     -d '{"model": "mistral-tiny", "messages": [{"role": "user", "content": "test"}]}'
   
   # Look for the "usage" field in the response
   ```

### Token Counts Are Zero

**Symptom:** Token counts show as 0 in reports.

**Solutions:**

1. **Mistral API response format:**
   - The proxy expects `usage.prompt_tokens` and `usage.completion_tokens` (OpenAI format)
   - Or `usage.input_tokens` and `usage.output_tokens` (alternative format)
   
2. **Check raw API response:**
   ```bash
   # Bypass proxy and call Mistral directly
   curl -X POST https://api.mistral.ai/v1/chat/completions \
     -H "Authorization: Bearer YOUR_API_KEY" \
     -H "Content-Type: application/json" \
     -d '{"model": "mistral-tiny", "messages": [{"role": "user", "content": "test"}]}'
   
   # Look for the usage field structure
   ```

3. **Add custom token counting:**
   If the API doesn't return usage information, you can set headers:
   ```bash
   curl -X POST http://localhost:8000/v1/chat/completions \
     -H "X-Telemetry-Request-Tokens: 100" \
     -H "X-Telemetry-Response-Tokens: 50" \
     -H "Content-Type: application/json" \
     -d '{"model": "mistral-tiny", "messages": [...]}'
   ```

### Database Errors

**Symptom:** Errors related to SQLite database.

**Solutions:**

1. **Database locked:**
   ```
   sqlite3.OperationalError: database is locked
   ```
   - Wait for other processes to finish
   - Ensure only one proxy instance is running
   - Check for long-running queries

2. **Database corruption:**
   ```bash
   # Try to repair
   sqlite3 telemetry.db "PRAGMA integrity_check;"
   
   # If corrupted, backup and recreate
   cp telemetry.db telemetry.db.corrupt
   rm telemetry.db
   # Restart proxy to recreate
   ```

3. **Disk full:**
   ```bash
   # Check disk space
   df -h
   
   # Free up space or move database
   ```

4. **Permission issues:**
   ```bash
   # Ensure directory is writable
   chmod 755 .
   chmod 666 telemetry.db
   ```

### Connection Errors to Mistral API

**Symptom:** Proxy returns 500 errors or connection timeouts.

**Solutions:**

1. **Check Mistral API status:**
   ```bash
   curl https://api.mistral.ai/v1/models
   ```

2. **Verify API endpoint:**
   ```bash
   python -c "from token_telemetry.config import load_config; c = load_config(); print(c.mistral.base_url)"
   ```

3. **Network connectivity:**
   ```bash
   # Test basic connectivity
   ping api.mistral.ai
   
   # Test HTTPS connectivity
   curl -v https://api.mistral.ai
   ```

4. **Proxy configuration:**
   - If you're behind a corporate proxy, configure it:
   ```bash
   export HTTP_PROXY=http://your-proxy:port
   export HTTPS_PROXY=http://your-proxy:port
   ```

5. **Timeout errors:**
   ```bash
   # Increase timeout in proxy.py (edit source code)
   # Change: timeout=30 to timeout=60 or higher
   ```

### Logging Issues

**Symptom:** No logs or logs not appearing.

**Solutions:**

1. **Check log file location:**
   ```bash
   python -c "from token_telemetry.config import load_config; c = load_config(); print(c.logging.file)"
   ```

2. **Check log level:**
   ```bash
   # Set to DEBUG for all messages
   python -m token_telemetry.cli proxy --verbose
   ```

3. **Log file permissions:**
   ```bash
   chmod 666 telemetry.log
   ```

4. **Logs not rotating:**
   - Currently, log rotation is not implemented
   - Manually rotate logs or use external tools like `logrotate`

### Python Version Issues

**Symptom:** Import errors or syntax errors.

**Solutions:**

1. **Check Python version:**
   ```bash
   python --version
   # Should be 3.11 or higher
   ```

2. **Use correct Python:**
   ```bash
   # If you have multiple Python versions
   python3.11 -m pip install -e .
   python3.11 -m token_telemetry.cli proxy
   ```

3. **Upgrade Python:**
   ```bash
   # macOS
   brew upgrade python
   
   # Linux
   sudo apt install python3.11
   
   # Windows
   # Download from https://www.python.org/downloads/
   ```

### Dependency Issues

**Symptom:** Module not found or import errors.

**Solutions:**

1. **Install missing dependencies:**
   ```bash
   pip install requests pyyaml
   ```

2. **Reinstall all dependencies:**
   ```bash
   pip uninstall token-telemetry
   pip install -e ".[dev]"
   ```

3. **Check virtual environment:**
   ```bash
   # Ensure you're in the correct environment
   which python
   which pip
   ```

4. **PyYAML not available:**
   ```bash
   pip install pyyaml
   # Or use JSON configuration files instead
   ```

## Error Messages Reference

### Database Errors

| Error | Cause | Solution |
|-------|-------|----------|
| `sqlite3.OperationalError: unable to open database file` | Database file path invalid or permissions issue | Check path and permissions |
| `sqlite3.OperationalError: database is locked` | Multiple processes accessing database | Wait or use WAL mode |
| `sqlite3.IntegrityError` | Database corruption | Restore from backup |

### Network Errors

| Error | Cause | Solution |
|-------|-------|----------|
| `requests.exceptions.ConnectionError` | Cannot connect to Mistral API | Check network and endpoint |
| `requests.exceptions.Timeout` | Request timed out | Increase timeout or check network |
| `requests.exceptions.HTTPError` | HTTP error response | Check API response and credentials |

### Configuration Errors

| Error | Cause | Solution |
|-------|-------|----------|
| `ValueError: Unsupported configuration file format` | Invalid file extension | Use .yaml, .yml, or .json |
| `ValueError: PyYAML is required` | PyYAML not installed | `pip install pyyaml` or use JSON |
| `AttributeError: module has no attribute` | Version mismatch | Reinstall package |

## Debug Mode

Enable debug mode for detailed troubleshooting:

```bash
# Start proxy with debug logging
python -m token_telemetry.cli proxy --verbose

# Or set environment variable
export LOG_LEVEL=DEBUG
python -m token_telemetry.cli proxy

# Check debug logs
tail -f telemetry.log
```

Debug logs include:
- All HTTP requests and responses
- Database operations
- Cost calculations
- Token extraction details
- Configuration loading

## Testing Your Setup

### Test 1: Basic Connectivity

```bash
# Start proxy
python -m token_telemetry.cli proxy &

# Test with curl
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "mistral-tiny", "messages": [{"role": "user", "content": "Hello"}]}'

# Expected: Should return a response (possibly 401 if no API key)
```

### Test 2: Data Logging

```bash
# Make a test call (with valid API key)
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -d '{"model": "mistral-tiny", "messages": [{"role": "user", "content": "Hello"}]}'

# Check if data was logged
python -m token_telemetry.cli report
```

### Test 3: Configuration Loading

```bash
# Create test config
mkdir -p config
echo "proxy:
  port: 9000" > config/local.yaml

# Start proxy with custom config
python -m token_telemetry.cli proxy --config config/local.yaml

# Verify port
netstat -tuln | grep 9000
```

## Performance Issues

**Symptom:** Proxy is slow or adding significant latency.

**Solutions:**

1. **Check processing time:**
   ```bash
   # Enable debug logging to see processing times
   python -m token_telemetry.cli proxy --verbose
   ```

2. **Database performance:**
   ```bash
   # Vacuum the database
   sqlite3 telemetry.db "VACUUM;"
   
   # Check database size
   ls -lh telemetry.db
   
   # If database is large, consider archiving old data
   ```

3. **Use WAL mode:**
   - Already enabled by default
   - Provides better concurrency for multiple connections

4. **Hardware resources:**
   - Ensure sufficient CPU and memory
   - Close other resource-intensive applications

## Still Having Issues?

### Collect Debug Information

```bash
# 1. Version information
python --version
pip show token-telemetry

# 2. Configuration
python -c "from token_telemetry.config import load_config; import pprint; pprint.pprint(load_config().__dict__)"

# 3. Environment variables
env | grep -E "(TELEMETRY|MISTRAL|VIBE)"

# 4. Database info
sqlite3 telemetry.db "SELECT COUNT(*) FROM calls; SELECT * FROM calls LIMIT 3;"

# 5. Proxy logs
tail -100 telemetry.log
```

### Create an Issue

When reporting an issue, include:

1. **Token Telemetry version**
2. **Python version**
3. **Operating system**
4. **Steps to reproduce**
5. **Error messages**
6. **Relevant configuration**
7. **Debug logs** (if applicable)

## Known Limitations

1. **No HTTPS support:** The proxy currently only supports HTTP. For production, use a reverse proxy like Nginx with SSL termination.

2. **No authentication:** The proxy doesn't authenticate clients. Anyone with access to the proxy port can use it.

3. **In-memory only:** Configuration is loaded at startup. Changes to config files require a restart.

4. **SQLite limitations:** For high-concurrency environments, consider using PostgreSQL (future enhancement).

5. **No persistent connections:** Each request creates a new connection to Mistral API.

## Workarounds

### HTTPS Support

Use Nginx or another reverse proxy:

```nginx
# nginx.conf
server {
    listen 443 ssl;
    server_name telemetry.yourdomain.com;
    
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### Authentication

Add basic authentication with Nginx:

```nginx
location / {
    auth_basic "Token Telemetry";
    auth_basic_user_file /etc/nginx/htpasswd;
    proxy_pass http://localhost:8000;
}
```

### High Availability

For production use, consider:
- Running multiple proxy instances behind a load balancer
- Using a more robust database like PostgreSQL
- Implementing health checks and monitoring

## See Also

- [Installation Guide](installation.md)
- [Usage Guide](usage.md)
- [Configuration Reference](configuration.md)
