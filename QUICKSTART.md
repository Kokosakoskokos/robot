# Clanker Robot - Quick Start Guide

## Installation

1. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **For hardware mode (Raspberry Pi), install additional packages:**
   ```bash
   # Uncomment relevant lines in requirements.txt, then:
   pip install RPi.GPIO adafruit-circuitpython-servokit adafruit-circuitpython-ssd1306 pynmea2 pyserial
   ```

## Running in Simulation Mode

Simulation mode allows you to test the robot without any hardware connected. All servo commands will print to the console.

## OpenRouter (Devstral free) setup

Clanker can use OpenRouter for its AI decisions. Set:

- **Windows PowerShell**:

```powershell
$env:OPENROUTER_API_KEY="YOUR_KEY_HERE"
```

- **Linux/macOS**:

```bash
export OPENROUTER_API_KEY="YOUR_KEY_HERE"
```

Then ensure `config/config.yaml` has:
- `ai.llm.enabled: true`
- `ai.llm.model: "mistralai/devstral-small:free"` (or your preferred model)

```bash
# Run autonomous mode
python main.py --simulation

# Run test sequence
python main.py --simulation --test

# Run example scripts
python examples/basic_usage.py
python examples/autonomous_demo.py
```

## Running with Hardware

1. **Connect hardware:**
   - PCA9685 servo controller (I2C)
   - 18 servos connected to PCA9685
   - Camera (USB or CSI)
   - GPS module (serial)
   - OLED display (I2C)

2. **Configure hardware settings in `config/config.yaml`**

3. **Run:**
   ```bash
   python main.py
   ```

## Project Structure

- `core/` - Core robot systems (hardware abstraction, main controller)
- `subsystems/` - Individual subsystems (servos, vision, navigation, display)
- `ai/` - AI brain, behaviors, and self-modification system
- `config/` - Configuration files
- `utils/` - Utility functions (logging)
- `examples/` - Example scripts

## Key Features

### Simulation Mode
- All servo commands print to console
- Camera returns black frames
- GPS returns simulated position
- Display messages print to console
- Perfect for development and testing

### Hardware Mode
- Full physical operation
- Real servo control via PCA9685
- Live camera feed
- GPS tracking
- OLED display output

### Self-Modification
The AI can analyze and modify its own code:
- Analyze codebase structure
- Find optimization opportunities
- Create new behaviors dynamically
- Modify existing functions (with safety checks)

### Behaviors
Built-in behaviors:
- **AvoidObstacleBehavior** - Avoids obstacles detected by vision
- **NavigateToTargetBehavior** - Navigates to GPS coordinates
- **ExploreBehavior** - Explores environment when no specific task

## Configuration

Edit `config/config.yaml` to configure:
- Servo geometry and addresses
- Camera settings
- GPS port and baudrate
- Display settings
- AI parameters

## Troubleshooting

### Import Errors
- Make sure all dependencies are installed: `pip install -r requirements.txt`
- Hardware-specific packages are optional in simulation mode

### Hardware Not Detected
- Check I2C connections: `i2cdetect -y 1`
- Verify serial port permissions: `ls -l /dev/ttyUSB0`
- Run in simulation mode to test without hardware

### Servo Issues
- Check PCA9685 address matches config
- Verify servo power supply
- Check servo connections

## Next Steps

1. Test in simulation mode first
2. Customize behaviors in `ai/behaviors.py`
3. Add new behaviors using the self-modification system
4. Tune servo geometry in config for your specific hexapod
5. Integrate additional sensors or capabilities

## Safety Notes

- Self-modification is enabled by default but can be disabled in config
- Always test new behaviors in simulation mode first
- Keep backups of working code
- The system creates `.backup` files before modifications
