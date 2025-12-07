"""
Windows Audio Manager - Smart device selection and management for Windows
Uses sounddevice with WASAPI for better Windows compatibility
"""

import logging
import numpy as np
from typing import Optional, List, Tuple

# Import sounddevice conditionally
try:
    import sounddevice as sd
    SOUNDDEVICE_AVAILABLE = True
except (ImportError, OSError):
    # OSError is raised when PortAudio library is not found
    sd = None
    SOUNDDEVICE_AVAILABLE = False


class WindowsAudioManager:
    """Manages audio device selection and testing for Windows"""
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.current_device = None
        self.device_info = None
        
        # Bluetooth keywords to avoid
        self.bluetooth_keywords = [
            'airpods', 'bluetooth', 'bt', 'headset', 
            'hands-free', 'wireless', 'buds'
        ]
        
        # Preferred device keywords (in priority order)
        self.preferred_keywords = [
            ['intel', 'smart sound'],
            ['realtek'],
            ['microphone array'],
            ['microphone'],
            ['mic']
        ]
    
    def list_all_devices(self) -> List[dict]:
        """List all available input devices"""
        if not SOUNDDEVICE_AVAILABLE:
            self.logger.warning("sounddevice not available - returning empty device list")
            return []
        
        devices = []
        all_devices = sd.query_devices()
        
        for i, dev in enumerate(all_devices):
            if dev['max_input_channels'] > 0:
                devices.append({
                    'index': i,
                    'name': dev['name'],
                    'channels': dev['max_input_channels'],
                    'sample_rate': dev['default_samplerate'],
                    'hostapi': sd.query_hostapis(dev['hostapi'])['name']
                })
        
        return devices
    
    def is_bluetooth_device(self, device_name: str) -> bool:
        """Check if device is Bluetooth (should be avoided)"""
        name_lower = device_name.lower()
        return any(kw in name_lower for kw in self.bluetooth_keywords)
    
    def get_device_priority(self, device_name: str) -> int:
        """Get priority score for device (lower is better)"""
        name_lower = device_name.lower()
        
        # Bluetooth devices get lowest priority
        if self.is_bluetooth_device(device_name):
            return 1000
        
        # Check preferred keywords
        for priority, keywords in enumerate(self.preferred_keywords):
            if any(kw in name_lower for kw in keywords):
                return priority
        
        # Default priority for unknown devices
        return 500
    
    def test_device(self, device_index: int, sample_rate: int = 16000) -> bool:
        """Test if a device can be opened successfully"""
        if not SOUNDDEVICE_AVAILABLE:
            self.logger.warning("sounddevice not available - cannot test device")
            return False
        
        try:
            # Try to open a test stream
            test_stream = sd.InputStream(
                device=device_index,
                channels=1,
                samplerate=sample_rate,
                dtype='int16',
                blocksize=1024,
                latency='high'  # More stable on Windows
            )
            
            # Try to read a small amount of data
            test_stream.start()
            data = test_stream.read(1024)
            test_stream.stop()
            test_stream.close()
            
            self.logger.debug(f"Device {device_index} test: SUCCESS")
            return True
            
        except Exception as e:
            self.logger.debug(f"Device {device_index} test: FAILED - {e}")
            return False
    
    def select_best_device(self, sample_rate: int = 16000) -> Optional[int]:
        """
        Select the best available audio device
        Returns device index or None if no device available
        """
        if not SOUNDDEVICE_AVAILABLE:
            self.logger.warning("sounddevice not available - cannot select device")
            return None
        
        devices = self.list_all_devices()
        
        if not devices:
            self.logger.error("No input devices found")
            return None
        
        # Sort devices by priority
        devices_with_priority = [
            (dev, self.get_device_priority(dev['name']))
            for dev in devices
        ]
        devices_with_priority.sort(key=lambda x: x[1])
        
        # Try devices in priority order
        for device, priority in devices_with_priority:
            device_idx = device['index']
            device_name = device['name']
            
            self.logger.info(f"Testing device {device_idx}: {device_name} (priority: {priority})")
            
            if self.test_device(device_idx, sample_rate):
                self.current_device = device_idx
                self.device_info = device
                self.logger.info(f"✅ Selected device: {device_name}")
                return device_idx
        
        self.logger.error("No working audio devices found")
        return None
    
    def get_device_info(self) -> Optional[dict]:
        """Get info about currently selected device"""
        return self.device_info
    
    def print_device_list(self):
        """Print formatted list of all devices"""
        if not SOUNDDEVICE_AVAILABLE:
            print("\nsounddevice not available - cannot list devices\n")
            return
        
        devices = self.list_all_devices()
        
        print("\n" + "=" * 70)
        print("AVAILABLE AUDIO DEVICES (sounddevice)")
        print("=" * 70)
        
        for dev in devices:
            is_bt = self.is_bluetooth_device(dev['name'])
            priority = self.get_device_priority(dev['name'])
            marker = "❌ BT" if is_bt else f"Priority: {priority}"
            
            print(f"\n{dev['index']}: {dev['name']}")
            print(f"   Channels: {dev['channels']} | Rate: {dev['sample_rate']} Hz")
            print(f"   Host API: {dev['hostapi']} | {marker}")
        
        print("\n" + "=" * 70 + "\n")
