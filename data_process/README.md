# Mind-Daemon Socket Interface

A real-time BCI data processing and transmission system that sends environment state and EEG-derived scores via socket connection.

## Features

- **Dynamic Score Calculation**: Calculates attention, excitement, relaxation, and stress scores from EEG data every second
- **Global Environment State**: Manages light, music, and curtain states in a thread-safe singleton
- **Socket Interface**: Sends `basic_params` data via socket connection every second
- **Real-time Data Processing**: Integrates with existing `sub_data_store` system for EEG/motion data collection

## Basic Parameters Format

```json
{
  "light": {
    "is_on": true,
    "color_hex": "#FF5733", 
    "lightness": 50
  },
  "music": {
    "is_playing": true,
    "name": "Aria De Capo",
    "type": "Relaxing"
  },
  "curtain": {
    "state": 0
  },
  "Scores": {
    "At": 50,
    "Ex": 50, 
    "Re": 50,
    "St": 50
  }
}
```

## Files

- `env_state.py`: Global environment state management system
- `socket_interface.py`: Main socket interface with BCI integration
- `demo.py`: Demonstration script without BCI hardware
- `test_system.py`: Complete system test with socket server

## Usage

### 1. Demo Mode (No BCI Hardware)
```bash
python3 demo.py
```

### 2. Testing with Socket Server
Terminal 1 - Start test server:
```bash
python3 test_system.py
```

Terminal 2 - Run socket interface:
```bash  
python3 socket_interface.py
```

### 3. Production Mode with BCI
1. Connect BCI headset via Emotiv Launcher
2. Configure your socket server to listen on `localhost:8888` 
3. Run the socket interface:
```bash
python3 socket_interface.py
```

## Configuration

Edit the main() function in `socket_interface.py` to customize:
- Socket host/port
- Transmission interval  
- BCI credentials
- Data streams

## Score Calculation

The system directly extracts four key metrics from BCI performance metrics (MET) data:
- **At (Attention)**: Derived from `foc` (focus) metric (0-100)  
- **Ex (Excitement)**: Derived from `exc` (excitement) metric (0-100)
- **Re (Relaxation)**: Derived from `rel` (relaxation) metric (0-100)
- **St (Stress)**: Derived from `str` (stress) metric (0-100)

Scores are updated in real-time when new MET data arrives from the BCI headset.

### MET Data Mapping
The system subscribes to `met` and `pow` data streams:
- `met` labels: `['eng.isActive', 'eng', 'exc.isActive', 'exc', 'lex', 'str.isActive', 'str', 'rel.isActive', 'rel', 'int.isActive', 'int', 'foc.isActive', 'foc']`
- Score extraction: `At=foc[12]`, `Ex=exc[3]`, `Re=rel[8]`, `St=str[6]` (converted from 0-1 to 0-100)

## Environment States

### Light State
- `is_on`: Boolean - light on/off
- `color_hex`: String - RGB color in hex format
- `lightness`: Integer 0-100 - brightness level

### Music State  
- `is_playing`: Boolean - music playing status
- `name`: String - current track name
- `type`: String - music type/category

### Curtain State
- `state`: Integer - 0 (open) or 1 (closed)

## Thread Safety

All components use proper locking mechanisms for thread-safe operation in multi-threaded environments.