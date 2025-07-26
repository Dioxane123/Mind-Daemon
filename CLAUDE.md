# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Mind Daemon is a BCI (Brain-Computer Interface) powered focus and productivity system designed for people who easily get distracted, especially ADHD patients. The system uses Emotiv BCI devices to monitor focus/attention levels and provides automated assistance through various modes.

## Architecture

The project follows a modular architecture with clear separation of concerns:

```
Mind-Daemon/
├── src/mind_daemon/        # Main Python package (uv-based)
│   ├── agent/             # Control center and state management
│   ├── bci/               # BCI data processing and Cortex API wrapper
│   ├── detect/            # Gesture detection and socket communication
│   ├── peripheral/        # Hardware controls (halo, music player)
│   └── utils/             # Shared utilities and communication
├── BCI/                   # Legacy BCI documentation
├── Agent/                 # Agent module documentation  
├── Detect/                # Gesture detection implementation
├── MCP_for_Agent/         # MCP service integration
├── peripheral/            # Hardware peripheral documentation
├── utils/                 # Legacy utilities documentation
├── python/                # Emotiv Cortex API examples and reference implementations
└── music/                 # Background music files for different environmental states
```

### Module Structure (src/mind_daemon/)

- **agent/**: Central control system using Minimax Agent
  - `control_center.py`: Main decision engine coordinating system responses
  - `state_manager.py`: Manages workflow states and transitions
- **bci/**: Brain-Computer Interface processing
  - `cortex.py`: Emotiv Cortex API wrapper
  - `data_subscriber.py`: EEG and performance metrics subscription
  - `trainer.py`: Mental command and facial expression training
- **detect/**: Gesture detection system
  - `gesture_detector.py`: Hand gesture recognition logic
  - `socket_client.py`: Communication with development board camera
- **peripheral/**: Hardware control interfaces
  - `halo_controller.py`: Screen edge lighting effects
  - `music_player.py`: Environmental audio management

## Core Workflow States

1. **Goal Setting**: User sets target and estimated completion time
2. **Focus Monitoring**: BCI monitors user's attention levels
3. **Relax Mode**: Triggered when focus drops below threshold
4. **Focus Preparation**: Background music and environmental adjustments
5. **Flow State**: Detected high focus, gradual reduction of assistance
6. **Long Rest**: Detected when user slumps in chair, auto-lock screen

## Development Commands

### Python Environment Setup (uv-based)

```bash
# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install project dependencies
uv sync

# Run in uv environment
uv run mind-daemon

# Install development dependencies
uv add --dev pytest ruff mypy

# Run specific modules
uv run python -m mind_daemon.bci.data_subscriber
uv run python -m mind_daemon.agent.control_center
```

### Legacy Python Examples (python/ directory)

```bash
# Run BCI data subscription example
uv run python python/sub_data.py

# Run mental command training
uv run python python/mental_command_train.py

# Run facial expression training  
uv run python python/facial_expression_train.py

# Run live advanced BCI processing
uv run python python/live_advance.py
```

### Main Application

```bash
# Run main halo effect (screen edge lighting)
uv run python Detect/halo.py
```

## BCI Module (Emotiv Cortex API)

The BCI functionality is built on Emotiv Cortex API with the following key components:

- **cortex.py**: Core Cortex API wrapper handling WebSocket connections and JSON-RPC requests
- **sub_data.py**: Subscribe to EEG, motion, performance metrics data streams
- **mental_command_train.py**: Train mental commands (neutral, push, pull)
- **facial_expression_train.py**: Train facial expressions (neutral, surprise, smile)
- **live_advance.py**: Live data processing with sensitivity controls
- **record.py**: Data recording and export functionality
- **marker.py**: Inject markers during data collection

### Required Dependencies (DO NOT USE APIS NOT MENTIONED)

- `websocket-client`: WebSocket communication with Cortex API
- `python-dispatch`: Event dispatcher for the Cortex wrapper

### BCI Setup Requirements

1. Download and install EMOTIV Launcher
2. Obtain Emotiv headset or create virtual device
3. Get Client ID & Secret from emotiv.com account
4. Authorize application on first run

## Agent Module

Uses Minimax Agent as the central control system to:

- Judge current environmental state
- Trigger appropriate system responses
- Coordinate between BCI input and system actions

## Detection Module

Implements gesture detection using:

- Development board with camera
- Socket communication with main system
- Continuous monitoring during Relax Mode
- Hand gesture recognition to trigger state transitions

## Key Integration Points

- **BCI → Agent**: Focus/attention level data feeds into decision engine
- **Agent → Peripheral**: Environmental controls (lighting, music, screen effects)
- **Detect → Agent**: Gesture inputs trigger mode transitions
- **MCP → Agent**: External service access and integrations

## File Structure Notes

- All module READMEs contain Chinese descriptions of functionality
- `python/` contains complete Emotiv API examples with comprehensive documentation
- `music/` contains ambient tracks for different focus states (relaxation vs concentration)
- `halo.py` implements screen edge lighting effects for soft notifications

## Development Guidelines

- Follow the modular architecture - each component has clear boundaries
- BCI module must only use Emotiv Cortex API as specified in examples
- Agent decisions should be based on BCI data and gesture inputs
- All hardware integrations go through the peripheral module
- Use existing music files for environmental audio - do not add new dependencies
