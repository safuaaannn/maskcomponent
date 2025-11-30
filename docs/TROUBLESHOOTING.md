# Troubleshooting Guide

## Issue 1: Kafka Connection Failed

### Problem
```
KafkaConnectionError: Unable to bootstrap from [('192.168.86.2', 9092)]
Connection timed out
```

### Solutions

#### Option A: Check Kafka Server Status

1. **Verify Kafka is running on the server:**
   ```bash
   # SSH to the Kafka server (192.168.86.2) and check
   ssh user@192.168.86.2
   # Then check if Kafka is running
   systemctl status kafka
   # Or check if port 9092 is listening
   netstat -tlnp | grep 9092
   ```

2. **Check network connectivity:**
   ```bash
   # From your machine
   ping 192.168.86.2
   telnet 192.168.86.2 9092
   ```

3. **Check firewall:**
   - Ensure port 9092 is open on the Kafka server
   - Check if your firewall allows outbound connections

#### Option B: Use Local Kafka (for testing)

If you can't connect to the remote Kafka, use a local one:

```bash
# Start local Kafka with Docker
docker run -d --name kafka -p 9092:9092 apache/kafka:latest

# Update environment to use localhost
export KAFKA_BOOTSTRAP_SERVERS=127.0.0.1:9092
source setup_env.sh  # This uses localhost
```

#### Option C: Check Kafka Configuration

The Kafka server might be configured to only listen on specific interfaces:

1. Check `server.properties` on Kafka server:
   ```properties
   listeners=PLAINTEXT://0.0.0.0:9092
   advertised.listeners=PLAINTEXT://192.168.86.2:9092
   ```

2. If Kafka is in Docker, ensure port mapping:
   ```bash
   docker run -p 9092:9092 ...
   ```

## Issue 2: Module Not Found

### Problem
```
ModuleNotFoundError: No module named 'maskcomponent'
```

### Solution

Use the wrapper script instead:

```bash
# Use the wrapper script (handles paths automatically)
python run_maskcomponent.py
```

Or set PYTHONPATH:

```bash
export PYTHONPATH=src:$PYTHONPATH
python -m maskcomponent.main
```

Or install in development mode:

```bash
pip install -e .
```

## Quick Fixes

### Test Kafka Connection

```bash
# Simple connectivity test
python test_kafka_simple.py

# Full connection test
python verify_kafka_connection.py
```

### Run Service with Correct Path

```bash
# Option 1: Use wrapper script
python run_maskcomponent.py

# Option 2: Set PYTHONPATH
PYTHONPATH=src:$PYTHONPATH python -m maskcomponent.main

# Option 3: Install package
pip install -e .
python -m maskcomponent.main
```

## Common Issues

### 1. Kafka Server Not Accessible

**Symptoms:**
- Connection timeout
- "Unable to bootstrap" error

**Fix:**
- Verify Kafka is running: `ssh user@192.168.86.2 "systemctl status kafka"`
- Check network: `ping 192.168.86.2`
- Check firewall rules
- Try local Kafka for testing

### 2. Wrong IP Address

**Symptoms:**
- Connection timeout
- Network unreachable

**Fix:**
- Verify IP: `ping 192.168.86.2`
- Check if IP changed: `arp -a | grep 192.168.86.2`
- Update `setup_env_custom.sh` with correct IP

### 3. Port Blocked

**Symptoms:**
- Connection timeout
- TCP connection fails

**Fix:**
- Check if port is open: `nc -zv 192.168.86.2 9092`
- Check firewall: `sudo ufw status` or `sudo iptables -L`
- Verify Kafka is listening: `netstat -tlnp | grep 9092` (on server)

### 4. Module Import Error

**Symptoms:**
- `ModuleNotFoundError: No module named 'maskcomponent'`

**Fix:**
- Use `python run_maskcomponent.py` (recommended)
- Or set `PYTHONPATH=src:$PYTHONPATH`
- Or install: `pip install -e .`

## Testing Checklist

```bash
# 1. Test network connectivity
ping 192.168.86.2

# 2. Test port connectivity
nc -zv 192.168.86.2 9092

# 3. Test Kafka connection
source setup_env_custom.sh
python test_kafka_simple.py

# 4. Test module import
python run_maskcomponent.py --help  # Should not error

# 5. Verify all components
python verify_setup.py
```

## Alternative: Use Local Services for Development

If remote Kafka is problematic, use local services:

```bash
# Start local services
docker run -d --name kafka -p 9092:9092 apache/kafka:latest
docker run -d --name minio -p 9000:9000 -p 9001:9001 \
  -e MINIO_ROOT_USER=admin -e MINIO_ROOT_PASSWORD=admin123 \
  minio/minio server /data --console-address ":9001"
docker run -d --name postgres -p 5432:5432 \
  -e POSTGRES_USER=admin_user -e POSTGRES_PASSWORD=password \
  -e POSTGRES_DB=kafka_db postgres:15

# Use localhost setup
source setup_env.sh
python run_maskcomponent.py
```

