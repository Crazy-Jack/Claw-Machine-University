# Step-by-Step Guide: Using Autolab with GLM-4.7

This guide shows you how to use Autolab with Zai's GLM-4.7 model for autonomous ML research.

## Overview

Autolab now supports two AI providers:
- **Anthropic Claude** (OpenClaw) - Original provider
- **Zai GLM-4.7** - Alternative with competitive pricing and strong reasoning

This guide focuses on setting up and using GLM-4.7.

## Step 1: Install Dependencies

```bash
# Navigate to autolab directory
cd /root/Claw-Machine-University/autolab

# Install Autolab and dependencies (includes zai-sdk)
pip3 install -e .
```

This installs:
- `zai-sdk>=1.0.0` - Zai's Python SDK for GLM-4.7
- All other Autolab dependencies

## Step 2: Get Your Zai API Key

1. Visit [Zhipu AI Platform](https://open.bigmodel.cn/)
2. Create an account or log in
3. Navigate to API Keys section
4. Generate a new API key
5. Save it securely

**Note:** API keys look like: `zai-xxxxxxxxxxxxx`

## Step 3: Configure GLM-4.7 Provider

### Option A: Environment Variable (Recommended)

```bash
# Set ZAI_API_KEY environment variable
export ZAI_API_KEY="your_zai_api_key_here"

# Make it persistent (add to ~/.bashrc or ~/.zshrc)
echo 'export ZAI_API_KEY="your_zai_api_key_here"' >> ~/.bashrc
source ~/.bashrc
```

### Option B: Configuration File

Edit the config file:

```bash
nano configs/openclaw.yaml
```

Update these settings:

```yaml
# Choose provider
provider: "zai"

# Zai (GLM-4.7) Configuration
zai_api_key: "your_zai_api_key_here"  # Your actual API key
zai_model: "glm-4.7"
zai_base_url: "https://open.bigmodel.cn/api/paas/v4/"  # For China
# zai_base_url: "https://api.z.ai/api/paas/v4/"  # For overseas

# Common Settings
max_tokens: 4096
temperature: 0.7
```

**Note:** If you set `ZAI_API_KEY` environment variable, you can leave `zai_api_key` as `null` in the config.

## Step 4: Verify GPU Workers

Check that your GPU workers are configured:

```bash
cat configs/gpu.yaml
```

The config includes:
- `34.48.207.147` - A100 40GB
- `136.107.43.189` - A100-SXM4 80GB

Test SSH connectivity:

```bash
ssh clawbot-tian@34.48.207.147 "nvidia-smi"
ssh clawbot-tian@136.107.43.189 "nvidia-smi"
```

You should see GPU information output.

## Step 5: Set Research Goal

Create a goal file:

```bash
mkdir -p autolab_workspace

cat > autolab_workspace/goal.txt << 'EOF'
Research Goal: Improve image classification accuracy on CIFAR-10

Objective Function: maximize val_accuracy
Baseline Accuracy: 92.5%

Constraints:
- Training time < 2 hours
- Model size < 50M parameters
- Use ResNet-18 architecture

Focus Areas:
1. Learning rate schedules
2. Data augmentation strategies
3. Regularization techniques
EOF
```

## Step 6: Test GLM-4.7 Connection

Run a quick test to ensure GLM-4.7 is working:

```bash
python3 << 'EOF'
from zai import ZaiClient
import os

api_key = os.environ.get("ZAI_API_KEY")
if not api_key:
    print("ERROR: ZAI_API_KEY not set")
    exit(1)

client = ZaiClient(api_key=api_key)

try:
    response = client.chat.completions.create(
        model="glm-4.7",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello! Please respond with 'GLM-4.7 is working!'"}
        ],
        temperature=0.3,
        max_tokens=50,
    )
    print("✓ GLM-4.7 Response:")
    print(response.choices[0].message.content)
except Exception as e:
    print(f"✗ Error: {e}")
EOF
```

Expected output:
```
✓ GLM-4.7 Response:
GLM-4.7 is working!
```

## Step 7: Run Autolab with GLM-4.7

### Option A: Single Cycle Test

```bash
# Run one cycle and exit
python3 -m autolab.controller.main --once --verbose
```

This will:
1. Load config and detect GLM-4.7 provider
2. Load research goal
3. Call GLM-4.7 with empty history
4. Agent proposes experiments
5. Validate and queue them
6. Exit

Output should show:
```
[2025-03-09 10:00:00] Starting Autolab Controller
[2025-03-09 10:00:00] Loading workspace: ./autolab_workspace
[2025-03-09 10:00:01] Provider: zai
[2025-03-09 10:00:01] Model: glm-4.7
[2025-03-09 10:00:02] Building context for Research Scientist...
[2025-03-09 10:00:05] Calling GLM-4.7 with research_scientist agent...
[2025-03-09 10:00:20] Agent response received
...
```

### Option B: Continuous Operation

```bash
# Start continuous loop
python3 -m autolab.controller.main --verbose
```

This runs indefinitely, cycling every 60 seconds.

### Option C: Run in Background (tmux)

```bash
# Start tmux session
tmux new -s autolab-glm

# In tmux, run controller
python3 -m autolab.controller.main --verbose

# Detach: Ctrl+B, then D

# Reattach later:
tmux attach -t autolab-glm
```

## Step 8: Monitor Progress

In separate terminals:

```bash
# Terminal 2: Watch queue
watch -n 5 python3 -m autolab.tools.show_queue

# Terminal 3: Watch history
watch -n 10 python3 -m autolab.tools.show_history

# Terminal 4: Check workers
python3 -m autolab.tools.check_workers --update

# Terminal 5: View failures
python3 -m autolab.tools.list_failures
```

## Step 9: View GLM-4.7 Planner Logs

GLM-4.7's planning decisions are logged to workspace:

```bash
# View raw planner inputs
ls -la autolab_workspace/planner_raw/*_input.json
cat autolab_workspace/planner_raw/<timestamp>_cycle_0001_input.json

# View raw planner outputs
ls -la autolab_workspace/planner_raw/*_output.json
cat autolab_workspace/planner_raw/<timestamp>_output.json
```

## Step 10: Compare with Anthropic (Optional)

You can easily switch between GLM-4.7 and Anthropic Claude:

```bash
# Switch to Anthropic Claude
# Edit configs/openclaw.yaml
nano configs/openclaw.yaml
# Change: provider: "anthropic"

# Set API key
export ANTHROPIC_API_KEY="your_anthropic_key"

# Run
python3 -m autolab.controller.main --once --verbose

# Switch back to GLM-4.7
# Edit configs/openclaw.yaml
nano configs/openclaw.yaml
# Change: provider: "zai"

# Set API key
export ZAI_API_KEY="your_zai_key"

# Run
python3 -m autolab.controller.main --once --verbose
```

## Troubleshooting GLM-4.7

### "zai package not installed"

```bash
# Install zai-sdk
pip3 install zai-sdk

# Or reinstall autolab
pip3 install -e .
```

### "No API key provided"

```bash
# Check environment variable
echo $ZAI_API_KEY

# Set it if not set
export ZAI_API_KEY="your_zai_api_key"

# Or edit config
nano configs/openclaw.yaml
# Set: zai_api_key: "your_zai_api_key"
```

### "Error calling GLM-4.7: API key invalid"

```bash
# Verify API key format (should start with "zai-")
echo $ZAI_API_KEY

# Regenerate API key from Zhipu AI platform if needed
```

### Connection Timeout

```bash
# Try different base URL if in China
nano configs/openclaw.yaml
# Use: https://open.bigmodel.cn/api/paas/v4/

# For overseas, use:
# https://api.z.ai/api/paas/v4/
```

### Agent Not Responding

```bash
# Check config
cat configs/openclaw.yaml | grep provider
# Should show: provider: "zai"

# Run verbose mode
python3 -m autolab.controller.main --verbose --once

# Check planner logs
cat autolab_workspace/planner_raw/*_output.json | tail -50
```

## GLM-4.7 vs Anthropic Claude Comparison

| Feature | GLM-4.7 | Anthropic Claude |
|---------|----------|-----------------|
| **Reasoning** | Strong complex planning | Excellent multi-step reasoning |
| **Speed** | Fast inference | Moderate speed |
| **Cost** | Competitive | Higher |
| **Language** | Chinese + English | Primarily English |
| **API** | Zhipu AI | Anthropic |
| **Model** | glm-4.7 | claude-3-5-sonnet |

## Advanced GLM-4.7 Configuration

### Adjust Temperature

Higher temperature = more creative, lower = more focused:

```yaml
# In configs/openclaw.yaml
temperature: 0.3  # Very focused (good for code)
temperature: 0.7  # Balanced (default)
temperature: 0.9  # Creative (good for exploration)
```

### Max Tokens

Control response length:

```yaml
max_tokens: 2048   # Shorter responses, faster
max_tokens: 4096   # Default
max_tokens: 8192   # Longer responses
```

### Custom System Prompts

You can modify system prompts in:
- `autolab/planner/prompts.py` - Modify `PLANNER_SYSTEM_PROMPT`

## Example: First GLM-4.7 Cycle

Here's what happens when you first run Autolab with GLM-4.7:

```bash
$ python3 -m autolab.controller.main --once --verbose

[2025-03-09 10:00:00] Starting Autolab Controller
[2025-03-09 10:00:00] Loading workspace: ./autolab_workspace
[2025-03-09 10:00:00] Loading experiments...
[2025-03-09 10:00:00] Found 0 experiments
[2025-03-09 10:00:00] Initializing GLM-4.7 bridge...
[2025-03-09 10:00:00] Provider: zai
[2025-03-09 10:00:00] Model: glm-4.7
[2025-03-09 10:00:01] Building context for Research Scientist...
[2025-03-09 10:00:01] Loading research goal from workspace/goal.txt
[2025-03-09 10:00:02] Context built (history: 0, queue: 0, failures: 0)
[2025-03-09 10:00:02] Calling GLM-4.7 with research_scientist agent...
[2025-03-09 10:00:15] GLM-4.7 response received (2.3s, 847 tokens)
[2025-03-09 10:00:15] Proposed action: create_experiment
[2025-03-09 10:00:15] Title: "Try learning rate 0.001 with AdamW optimizer"
[2025-03-09 10:00:15] Family: lr_sweep
[2025-03-09 10:00:15] Validating action...
[2025-03-09 10:00:15] Action validated
[2025-03-09 10:00:15] Created experiment: exp_001
[2025-03-09 10:00:15] Status: pending -> ready
[2025-03-09 10:00:15] Calling Experiment Operator...
[2025-03-09 10:00:16] Dispatching to worker a100x1-001...
[2025-03-09 10:00:16] Status: ready -> running
[2025-03-09 10:00:16] SSH command: python3 train.py --config exp_001_config.json
[2025-03-09 10:00:20] Monitoring job on a100x1-001...
[2025-03-09 11:30:00] Job completed successfully
[2025-03-09 11:30:01] Parsing results from results.json
[2025-03-09 11:30:02] Found metrics: val_accuracy=85.2, training_time_seconds=3600
[2025-03-09 11:30:02] Status: running -> completed
[2025-03-09 11:30:03] Cycle complete. Sleeping...
```

## Next Steps

After your first cycle:

1. Review results:
   ```bash
   python3 -m autolab.tools.show_history --detailed
   ```

2. Mark best as baseline:
   ```bash
   python3 -m autolab.tools.mark_baseline <experiment_id> --family cifar10
   ```

3. Run more cycles:
   ```bash
   python3 -m autolab.controller.main --verbose
   ```

4. Generate reports:
   ```bash
   python3 -m autolab.tools.generate_cycle_report --cycle 1
   ```

## Support

For GLM-4.7 specific issues:
- [Zhipu AI Platform](https://open.bigmodel.cn/)
- [Zai SDK Documentation](https://github.com/zai-org/z-ai-sdk-python)
- Autolab GitHub Issues

For Autolab issues:
- Check `autolab_workspace/planner_raw/*_output.json` for errors
- Run with `--verbose` flag
- Review logs in `autolab_workspace/logs/`
