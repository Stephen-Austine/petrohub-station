import time
import requests

def ping_location():
    """
    Ping current location and print to terminal
    Uses ipinfo.io which has more generous free limits
    """
    try:
        # Get location from ipinfo.io (more generous free limits)
        response = requests.get('https://ipinfo.io/json', timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            # Extract location information
            ip = data.get('ip', 'Unknown')
            location = data.get('loc', 'Unknown')
            city = data.get('city', 'Unknown')
            region = data.get('region', 'Unknown')
            country = data.get('country', 'Unknown')
            org = data.get('org', 'Unknown')  # ISP/organization
            
            if location != 'Unknown':
                lat, lng = location.split(',')
            else:
                lat, lng = 'Unknown', 'Unknown'
            
            # Print location info
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Location Update:")
            print(f"  IP Address: {ip}")
            print(f"  ISP/Org: {org}")
            print(f"  Location: {city}, {region}, {country}")
            print(f"  Coordinates: {lat}, {lng}")
            print("-" * 50)
            
        else:
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Error: Could not fetch location")
            print(f"  Status Code: {response.status_code}")
            print("-" * 50)
            
    except requests.exceptions.RequestException as e:
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Network Error: {e}")
        print("-" * 50)
    except Exception as e:
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Error: {e}")
        print("-" * 50)

def ping_location_backup():
    """
    Backup location ping using a different service
    """
    try:
        # Alternative service - ip-api.com (1000 requests per hour free)
        response = requests.get('http://ip-api.com/json/', timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            # Extract location information
            ip = data.get('query', 'Unknown')
            city = data.get('city', 'Unknown')
            region = data.get('regionName', 'Unknown')
            country = data.get('country', 'Unknown')
            lat = data.get('lat', 'Unknown')
            lng = data.get('lon', 'Unknown')
            isp = data.get('isp', 'Unknown')
            
            # Print location info
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Location Update (Backup):")
            print(f"  IP Address: {ip}")
            print(f"  ISP: {isp}")
            print(f"  Location: {city}, {region}, {country}")
            print(f"  Coordinates: {lat}, {lng}")
            print("-" * 50)
            
        else:
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Error: Could not fetch location (Backup)")
            print(f"  Status Code: {response.status_code}")
            print("-" * 50)
            
    except requests.exceptions.RequestException as e:
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Network Error (Backup): {e}")
        print("-" * 50)
    except Exception as e:
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Error (Backup): {e}")
        print("-" * 50)

# Example usage:
if __name__ == '__main__':
    # Call the function whenever you want to ping location
    ping_location()
    
    # If ipinfo.io doesn't work, try the backup
    # ping_location_backup()