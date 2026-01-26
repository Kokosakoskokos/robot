# Clanker - Autonomous Hexapod Robot System

Clanker is an autonomous hexapod robot system built on Raspberry Pi that combines artificial intelligence, computer vision, hardware control, and navigation capabilities. The entire system is designed to be self-aware and self-modifying, meaning the AI can read and edit its own code, create new behaviors, and optimize its performance over time.

## Features

- **Autonomous Hexapod Locomotion**: 6-legged robot with 18 servo motors (3 per leg)
- **Computer Vision**: Real-time object detection and environment awareness
- **Self-Modifying AI**: Can read, analyze, and modify its own code
- **Dual Mode Operation**: 
  - Simulation Mode: Test without hardware, all commands print to console
  - Hardware Mode: Full physical operation with servos, GPS
- **Modular Architecture**: Independent subsystems with well-defined interfaces
- **GPS Navigation**: Location tracking and path planning

## Project Structure

```
clanker/
├── config/
│   └── config.yaml          # Configuration settings
├── core/
│   ├── __init__.py
│   ├── robot.py             # Main robot controller
│   └── hardware.py          # Hardware abstraction layer
├── subsystems/
│   ├── __init__.py
│   ├── servos.py            # Hexapod servo control
│   ├── vision.py            # Computer vision module
│   └── navigation.py        # GPS and navigation
├── ai/
│   ├── __init__.py
│   ├── brain.py             # AI core and decision making
│   ├── self_modify.py       # Self-modification capabilities
│   └── behaviors.py         # Behavior system
├── utils/
│   ├── __init__.py
│   └── logger.py            # Logging utilities
├── main.py                  # Entry point
├── requirements.txt         # Python dependencies
└── README.md
```

## Installation

1. Clone this repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Configure hardware + AI settings in `config/config.yaml`

## OpenRouter (Devstral free) setup

Clanker’s AI can use **OpenRouter** (for example the **Devstral free** model) to decide actions. Set an environment variable:

- **Windows PowerShell**:

```powershell
$env:OPENROUTER_API_KEY="YOUR_KEY_HERE"
```

- **Linux/macOS**:

```bash
export OPENROUTER_API_KEY="YOUR_KEY_HERE"
```

Optional (for OpenRouter headers/analytics):
- `OPENROUTER_SITE_URL`
- `OPENROUTER_APP_NAME`

4. Run in simulation mode:
   ```bash
   python main.py --simulation
   ```

5. Run with hardware:
   ```bash
   python main.py
   ```

## Configuration

Edit `config/config.yaml` to configure:
- Servo pin assignments
- Camera settings
- GPS module settings
- OLED display settings
- AI parameters
- Simulation/hardware mode

## Architecture

The system is built with modularity in mind - each subsystem operates independently but communicates through well-defined interfaces. This makes it easy to:
- Upgrade individual components
- Debug specific subsystems
- Replace hardware without rewriting entire system
- Test components in isolation

## License

MIT License
