"""Windows permissions and diagnostics utilities."""

import logging
import subprocess
import winreg
from typing import Optional, Dict, List

logger = logging.getLogger(__name__)


class WindowsPermissions:
    """Check and guide user through Windows permissions."""
    
    @staticmethod
    def check_microphone_permissions() -> Optional[bool]:
        """
        Check if Windows allows microphone access.
        
        Returns:
            True if allowed, False if denied, None if cannot determine
        """
        try:
            # Check registry for microphone permission
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\CapabilityAccessManager\ConsentStore\microphone"
            )
            value, _ = winreg.QueryValueEx(key, "Value")
            winreg.CloseKey(key)
            
            if value == "Allow":
                logger.info("✅ Microphone permission: Allowed")
                return True
            elif value == "Deny":
                logger.warning("⚠️  Microphone permission: Denied")
                return False
            else:
                logger.info(f"ℹ️  Microphone permission: {value}")
                return None
                
        except FileNotFoundError:
            logger.warning("⚠️  Cannot determine microphone permissions")
            return None
        except Exception as e:
            logger.error(f"❌ Error checking permissions: {e}")
            return None
    
    @staticmethod
    def open_microphone_settings():
        """Open Windows microphone privacy settings."""
        try:
            subprocess.run(["start", "ms-settings:privacy-microphone"], shell=True)
            logger.info("📱 Opening microphone settings...")
        except Exception as e:
            logger.error(f"❌ Failed to open settings: {e}")
    
    @staticmethod
    def check_audio_services() -> Dict[str, bool]:
        """
        Check if Windows audio services are running.
        
        Returns:
            Dictionary of service names and their running status
        """
        services = {
            "Audiosrv": False,  # Windows Audio
            "AudioEndpointBuilder": False  # Windows Audio Endpoint Builder
        }
        
        try:
            for service_name in services.keys():
                result = subprocess.run(
                    ["sc", "query", service_name],
                    capture_output=True,
                    text=True
                )
                
                if "RUNNING" in result.stdout:
                    services[service_name] = True
                    logger.info(f"✅ {service_name}: Running")
                else:
                    logger.warning(f"⚠️  {service_name}: Not running")
                    
        except Exception as e:
            logger.error(f"❌ Error checking services: {e}")
        
        return services
    
    @staticmethod
    def get_processes_using_microphone() -> List[str]:
        """
        Get list of processes that might be using the microphone.
        
        Returns:
            List of process names
        """
        common_mic_apps = [
            "teams.exe", "discord.exe", "zoom.exe", "skype.exe",
            "chrome.exe", "msedge.exe", "firefox.exe",
            "obs64.exe", "obs32.exe"
        ]
        
        running_apps = []
        
        try:
            result = subprocess.run(
                ["tasklist"],
                capture_output=True,
                text=True
            )
            
            for app in common_mic_apps:
                if app.lower() in result.stdout.lower():
                    running_apps.append(app)
                    logger.info(f"⚠️  Found: {app}")
                    
        except Exception as e:
            logger.error(f"❌ Error checking processes: {e}")
        
        return running_apps
    
    @staticmethod
    def suggest_fixes():
        """Print suggestions for fixing microphone access issues."""
        print("\n" + "="*60)
        print("🔧 MICROPHONE TROUBLESHOOTING")
        print("="*60)
        
        # Check permissions
        perm = WindowsPermissions.check_microphone_permissions()
        if perm is False:
            print("\n❌ Issue: Microphone access is DENIED")
            print("   Fix: Enable microphone access in Windows Settings")
            print("   Run: WindowsPermissions.open_microphone_settings()")
        elif perm is None:
            print("\n⚠️  Cannot determine microphone permissions")
        
        # Check services
        services = WindowsPermissions.check_audio_services()
        if not all(services.values()):
            print("\n❌ Issue: Audio services not running")
            print("   Fix: Restart Windows Audio services")
            print("   Run as Admin: net start Audiosrv")
        
        # Check apps
        apps = WindowsPermissions.get_processes_using_microphone()
        if apps:
            print("\n⚠️  Issue: Other apps may be using the microphone")
            print(f"   Found: {', '.join(apps)}")
            print("   Fix: Close these apps and try again")
        
        print("\n" + "="*60)
        print("💡 Quick Fixes:")
        print("   1. Close all browsers (Chrome, Edge, Firefox)")
        print("   2. Close communication apps (Teams, Discord, Zoom)")
        print("   3. Restart your computer")
        print("   4. Check Device Manager → Audio inputs → Enable device")
        print("="*60 + "\n")
