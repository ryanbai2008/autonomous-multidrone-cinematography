import sys
import socket
import os
import platform
import subprocess
import re
import time

class WifiBind:
    def __init__(self, adapter, tello_ip, wifi_adapter_ip):
        self.adapter = adapter
        self.tello_ip = tello_ip
        self.wifi_adapter_ip = wifi_adapter_ip

        
    def run_command(self, command):
        """Runs a system command and returns output."""
        try:
            result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            print(f"Error running command: {e}")
            return None

    def get_connected_ssid(self):
        """Returns the SSID of the currently connected network for the given adapter."""
        system = platform.system()
        
        if system == "Windows":
            result = self.run_command('netsh wlan show interfaces')
            match = re.search(r"(?:IP Address|IPv4 Address)[\s.]+:\s+([\d.]+)", result)
            return match.group(1) if match else None
        elif system in ["Linux", "Darwin"]:
            result = self.run_command(f'nmcli -t -f active,ssid dev wifi | grep "^yes"')
            return result.strip().split(":")[-1] if result else None
        return None


    def connect_wifi(self, ssid):
        """Connects Wi-Fi adapter to a specific Tello network only if not already connected."""
        current_ssid = self.get_connected_ssid(self.adapter)
        
        if current_ssid == ssid:
            print(f"{self.adapter} is already connected to {ssid}. Skipping connection.")
            return
        
        print(f"Connecting {self.adapter} to {ssid}...")
        system = platform.system()
        
        if system == "Windows":
            self.run_command(f'netsh wlan connect name="{ssid}" interface="{self.adapter}"')
        else:  # Linux/macOS
            self.run_command(f'nmcli device wifi connect "{ssid}" ifname {self.adapter}')
        
        time.sleep(0.1)

    def get_current_ip(self):
        """Returns the current IP address of the Wi-Fi adapter."""
        system = platform.system()
        
        if system == "Windows":
            result = self.run_command(f'netsh interface ip show address name="{self.adapter}"')
            match = re.search(r"IP Address:\s+([\d.]+)", result)
            return match.group(1) if match else None
        elif system in ["Linux", "Darwin"]:
            result = self.run_command(f'ip addr show {self.adapter}')
            match = re.search(r'inet (\d+\.\d+\.\d+\.\d+)/', result)
            return match.group(1) if match else None
        return None

    def set_static_ip(self):
        """Assigns a static IP to the Wi-Fi adapter only if it is not already set."""
        current_ip = self.get_current_ip(self.adapter)
        
        if current_ip == self.wifi_adapter_ip:
            print(f"Static IP for {self.adapter} is already {self.wifi_adapter_ip}. Skipping.")
            return
        
        print(f"Setting static IP {self.wifi_adapter_ip} for {self.adapter}...")
        system = platform.system()
        
        if system == "Windows":
            self.run_command(f'netsh interface ip set address name="{self.adapter}" static {self.wifi_adapter_ip} 255.255.255.0')
        else:  # Linux/macOS
            self.run_command(f'sudo ifconfig {self.adapter} {self.wifi_adapter_ip} netmask 255.255.255.0 up')


    def check_route(self, ip):
        """Checks if a route already exists for the given IP."""
        system = platform.system()
        
        if system == "Windows":
            result = self.run_command("route print")
        elif system in ["Linux", "Darwin"]:
            result = self.run_command("ip route show")
        else:
            return False
        
        return ip in result if result else False

    def add_route(self, adapter_num):
        """Adds routing rules only if they do not already exist for each adapter."""
        system = platform.system()


        route_exists = self.check_route(self.wifi_adapter_ip)

        if route_exists:
            print(f"Routes for {self.tello_ip} already exist. Skipping.")
            return

        print(f"Adding missing route(s) for {self.tello_ip}...")

        if system == "Windows":
            if not route_exists:
                self.run_command(f'route -p add {self.tello_ip} mask 255.255.255.255 {self.wifi_adapter_ip} metric 1')
        elif system in ["Linux", "Darwin"]:
            if not route_exists:
                self.run_command(f'sudo ip route add {self.tello_ip} via {self.wifi_adapter_ip} dev wlan' + str(adapter_num))
           